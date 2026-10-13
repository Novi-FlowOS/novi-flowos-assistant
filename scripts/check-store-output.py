"""Fail publication when the builder skipped the application or kept placeholders."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("output", nargs="?", default="dist")
args = parser.parse_args()
root = Path(args.output)
for name in ("store.json", "index.json"):
    with (root / name).open(encoding="utf-8") as handle:
        json.load(handle)
compose = root / "apps/pl.org.novi.flowos-assistant/docker-compose.yml"
text = compose.read_text(encoding="utf-8")
if any(placeholder in text for placeholder in ("YOUR_GITHUB_USER", "YOUR_REPO", "your_github_user", "your_repo")):
    raise SystemExit("Store still contains example image names; run prepare-github.py first.")
if "ghcr.io/" not in text:
    raise SystemExit("Published application image is missing.")
print("Store protocol files and application compose verified.")
