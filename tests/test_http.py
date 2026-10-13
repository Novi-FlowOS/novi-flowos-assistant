import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "reference/logs").mkdir(parents=True)
        (cls.root / "reference/logs/build.log").write_text("FAILED: test\nerror: libncurses.so.5\n")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = dict(os.environ, STATE_ROOT=str(cls.root / "state"), SYSTEM_ROOT=str(cls.root / "reference"), SSD_ROOT=str(cls.root / "ssd"), CDN_ROOT=str(cls.root / "cdn"), PORT=str(cls.port), OLLAMA_URL="http://127.0.0.1:1", PANEL_ACCESS_KEY="test-only-key")
        cls.process = subprocess.Popen([sys.executable, str(ROOT / "app/server.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(80):
            try:
                urllib.request.urlopen(cls.base + "/healthz", timeout=.2).close()
                break
            except OSError:
                time.sleep(.05)
        else:
            cls.process.terminate()
            raise RuntimeError("HTTP server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.temp.cleanup()

    def request(self, path, payload=None, authorized=True):
        headers = {"Content-Type": "application/json"}
        if authorized:
            headers["Authorization"] = "Bearer test-only-key"
        request = urllib.request.Request(self.base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)

    def test_authentication_required(self):
        status, _ = self.request("/api/discover", authorized=False)
        self.assertEqual(status, 401)

    def test_read_only_folder_detection(self):
        status, result = self.request("/api/discover")
        self.assertEqual(status, 200)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["logs"], ["build.log"])

    def test_log_path_escape_is_rejected(self):
        status, result = self.request("/api/diagnose", {"log": "../../state/access-key"})
        self.assertEqual(status, 400)

    def test_no_model_is_honestly_reported(self):
        status, result = self.request("/api/diagnose", {"log": "build.log"})
        self.assertEqual(status, 200)
        self.assertIn("ai_error", result)
        self.assertNotIn("ai", result)
        self.assertFalse(result["changed_files"])
        self.assertTrue(result["hints"])

    def test_no_build_endpoint(self):
        status, _ = self.request("/api/build", {})
        self.assertEqual(status, 404)

    def test_html_and_browser_policy(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as response:
            page = response.read().decode()
            self.assertIn("Novi", page)
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_upload_apk_is_staged_and_deduplicated(self):
        import io
        import zipfile
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr("AndroidManifest.xml", '<manifest package="pl.novi.upload"/>')
        for duplicate in (False, True):
            req = urllib.request.Request(self.base + "/api/apps/upload", data=content.getvalue(), headers={"Authorization": "Bearer test-only-key", "X-Filename": "Test.apk", "Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result["duplicate"], duplicate)
            self.assertFalse(result["installed"])
            self.assertTrue(result["staging_only"])
        self.assertFalse((self.root / "reference/apps").exists())
        status, result = self.request("/api/apps")
        self.assertEqual(status, 200)
        self.assertTrue(any(app["package"] == "pl.novi.upload" for app in result["apps"]))

if __name__ == "__main__":
    unittest.main()
