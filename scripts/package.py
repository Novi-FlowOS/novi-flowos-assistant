from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
target = root.parent / "novi-flowos-assistant.zip"
with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob("*")):
        rel = file.relative_to(root)
        if file.is_file() and not any(part in {".git", "__pycache__", "state", "screenshots-local", ".store-tools", "dist", "out", ".cache"} for part in rel.parts) and file.suffix not in {".pyc", ".zip", ".apk"} and file.name != ".env":
            archive.write(file, str(Path(root.name) / rel))
print(target)
