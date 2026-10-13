import hmac
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import ResearchError, ai_answer, baseline_diagnosis, discover, log_excerpt, search_devices, research, tail, identify_device, application_list, apk_identity

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("STATE_ROOT", "/state"))
SYSTEM = Path(os.environ.get("SYSTEM_ROOT", "/reference/system"))
SSD = Path(os.environ.get("SSD_ROOT", "/reference/ssd"))
CDN = Path(os.environ.get("CDN_ROOT", "/reference/cdn"))
STATE.mkdir(parents=True, exist_ok=True)
ADDED_APPS = STATE / "added-apps"
ADDED_APPS.mkdir(exist_ok=True)
key_path = STATE / "access-key"
if not key_path.exists():
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(secrets.token_urlsafe(32))
TOKEN = os.environ.get("PANEL_ACCESS_KEY") or key_path.read_text().strip()
RATE_LOCK = threading.Lock()
FAILURES = {}

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # Avoid logging query strings, access keys, log contents and model prompts.
        print(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args)>1 else ''}", flush=True)

    def send(self, code, data, mime="application/json"):
        payload = json.dumps(data, ensure_ascii=False).encode() if mime == "application/json" else data
        self.send_response(code)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def auth(self):
        address = self.client_address[0]
        with RATE_LOCK:
            now = time.monotonic()
            recent = [t for t in FAILURES.get(address, []) if now - t < 60]
            if len(recent) >= 12:
                self.send(429, {"error": "Zbyt wiele prób logowania. Poczekaj minutę."})
                return False
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if not hmac.compare_digest(supplied.encode(), TOKEN.encode()):
                FAILURES[address] = recent + [now]
                self.send(401, {"error": "Podaj klucz dostępu do panelu."})
                return False
            FAILURES.pop(address, None)
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
            self.send(403, {"error": "Żądanie z innej strony jest odrzucone."})
            return False
        return True

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/healthz":
            return self.send(200, {"status": "ok", "version": "0.1.0"})
        static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/icon.svg": "icon.svg"}
        if path in static:
            file = ROOT / "web" / static[path]
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}[file.suffix]
            return self.send(200, file.read_bytes(), mime)
        if not path.startswith("/api/") or not self.auth():
            if not path.startswith("/api/"):
                self.send(404, {"error": "Nie znaleziono."})
            return
        try:
            if path == "/api/discover":
                return self.send(200, discover(SYSTEM, SSD, CDN))
            if path == "/api/devices":
                query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                return self.send(200, {"devices": search_devices(query)})
            if path == "/api/apps":
                return self.send(200, application_list(SYSTEM / "apps", ADDED_APPS))
            self.send(404, {"error": "Nie znaleziono."})
        except (ValueError, ResearchError) as exc:
            self.send(400, {"error": str(exc)})
        except OSError:
            self.send(503, {"error": "Nie można odczytać folderów. Sprawdź montowania tylko do odczytu."})

    def do_POST(self):
        if not self.auth():
            return
        if self.path == "/api/apps/upload":
            return self.upload_apk()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 250_000:
                return self.send(413, {"error": "Za duże żądanie; limit 250 KB."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Niepoprawne dane.")
            if self.path == "/api/identify":
                return self.send(200, identify_device(data.get("query", "")))
            if self.path == "/api/research":
                result = research(data.get("vendor", ""), data.get("codename", ""), data.get("android", "12L"))
                # Model input contains compact verified source facts, not arbitrary web pages.
                if data.get("use_ai"):
                    try:
                        result["ai"] = ai_answer("sources", result)
                    except (ValueError, ResearchError) as exc:
                        result["ai_error"] = str(exc) + " Sprawdź Ollama i pobrany model; źródła poniżej pozostają wynikiem weryfikacji HTTP."
                return self.send(200, result)
            if self.path == "/api/diagnose":
                text = data.get("text", "")
                if data.get("log"):
                    log = str(data["log"])
                    root = (SYSTEM / "logs").resolve()
                    file = (root / log).resolve()
                    if file.parent != root or file.suffix != ".log" or not file.is_file():
                        raise ValueError("Wybierz istniejący plik .log w katalogu logów.")
                    text = tail(file)
                excerpt = log_excerpt(text)
                if not excerpt.strip():
                    raise ValueError("Wklej log albo wybierz plik z listy.")
                result = {"excerpt": excerpt, "hints": baseline_diagnosis(excerpt), "changed_files": False}
                try:
                    result["ai"] = ai_answer("diagnose", {"log_excerpt": excerpt, "hints": result["hints"]})
                except (ValueError, ResearchError) as exc:
                    result["ai_error"] = str(exc) + " To wskazówki regułowe, nie odpowiedź AI."
                return self.send(200, result)
            self.send(404, {"error": "Nie znaleziono."})
        except (ValueError, TypeError, ResearchError) as exc:
            self.send(400, {"error": str(exc)})
        except OSError:
            self.send(503, {"error": "Nie udało się odczytać logu."})

    def upload_apk(self):
        temporary = None
        try:
            self.connection.settimeout(60)
            name = urllib.parse.unquote(self.headers.get("X-Filename", ""))
            length = int(self.headers.get("Content-Length", "0"))
            if not name.lower().endswith(".apk") or len(name) > 160 or any(c in name for c in "/\\\x00\r\n"):
                raise ValueError("Wybierz plik aplikacji z końcówką .apk.")
            if not 0 < length <= 128 * 1024**2:
                self.close_connection = True
                return self.send(413, {"error": "APK musi mieć mniej niż 128 MB."})
            if shutil.disk_usage(ADDED_APPS).free < length + 32 * 1024**2:
                self.close_connection = True
                return self.send(507, {"error": "Za mało miejsca na dodanie aplikacji."})
            digest = hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=ADDED_APPS, suffix=".upload", delete=False) as file:
                temporary = Path(file.name)
                remaining = length
                while remaining:
                    block = self.rfile.read(min(1024**2, remaining))
                    if not block:
                        raise ValueError("Przesyłanie pliku zostało przerwane.")
                    file.write(block)
                    digest.update(block)
                    remaining -= len(block)
            identity = apk_identity(temporary)
            sha = digest.hexdigest()
            target = ADDED_APPS / (sha + ".apk")
            duplicate = target.exists()
            if not duplicate:
                temporary.replace(target)
                temporary = None
                target.with_suffix(".json").write_text(json.dumps({"name": name}, ensure_ascii=False), encoding="utf-8")
            return self.send(200, {"name": name, "sha256": sha, "duplicate": duplicate, "staging_only": True, "installed": False, **identity})
        except (ValueError, OSError) as exc:
            self.close_connection = True
            self.send(400, {"error": str(exc) if isinstance(exc, ValueError) else "Nie udało się zapisać aplikacji."})
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

if __name__ == "__main__":
    server = ThreadingHTTPServer((os.environ.get("BIND_HOST", "0.0.0.0"), int(os.environ.get("PORT", "8080"))), Handler)
    server.daemon_threads = True
    print("Novi FlowOS Assistant: read-only mode; key stored in /state/access-key", flush=True)
    server.serve_forever()
