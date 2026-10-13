"""Render a ZimaOS import file for the user's chosen GitHub repository."""
import argparse
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("repository", help="GitHub owner/repository")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", args.repository):
    parser.error("Expected owner/repository")
owner, repo = args.repository.split("/")
source = (root / "docker-compose.yml").read_text(encoding="utf-8")
source = source.replace("    build: .\n", "").replace("image: novi-flowos-assistant:local", f"image: ghcr.io/{args.repository.lower()}:latest")
source = source.replace("YOUR_GITHUB_USER", owner).replace("YOUR_REPO", repo)
# A store installation includes AI; manual development Compose keeps it optional.
source = source.replace("    profiles:\n      - ai\n", "")
source = source.replace("AI profile is optional; 2 GB RAM limit.", "Local AI downloads its model on first installation; 2 GB RAM limit.")
source = source.replace("AI jest opcjonalne, limit 2 GB RAM.", "Model AI pobiera się przy pierwszej instalacji, limit 2 GB RAM.")
source = source.replace("      OLLAMA_MODEL: qwen3:0.6b", "      OLLAMA_MODEL: qwen3:0.6b\n      PANEL_ACCESS_KEY: \"\"")
# Reference roots may not exist yet on a new machine. Creating empty mount roots
# does not create or overwrite a firmware project.
source = source.replace("        read_only: true", "        read_only: true\n        bind:\n          create_host_path: true")
source = source.replace("    - arm64\n  version:", "    - arm64\n  repo: https://github.com/" + args.repository + "\n  version:")
target = root / "Apps" / "NoviFlowOSAssistant" / "docker-compose.yml"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(source, encoding="utf-8")
assets = target.parent
(assets / "icon.svg").write_bytes((root / "app/web/icon.svg").read_bytes())
config_path = root / "store-config.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
config["store_id"] = f"novi-{owner.lower()}-{repo.lower()}"
config["maintainer"] = owner
config["url"] = f"https://github.com/{args.repository}"
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(target)
print(f"Import URL: https://raw.githubusercontent.com/{args.repository}/main/Apps/NoviFlowOSAssistant/docker-compose.yml")
print(f"Store v2 URL: https://{owner.lower()}.github.io/{repo}/")
print(f"Store v1 URL: https://{owner.lower()}.github.io/{repo}/store/main.zip")
