"""Verify anonymous pull before publishing a store that users should install."""
import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("repository")
args = parser.parse_args()
repository = args.repository.lower()
if not re.fullmatch(r"[a-z0-9_-]+/[a-z0-9_.-]+", repository):
    parser.error("Expected owner/repository")
try:
    query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    with urllib.request.urlopen("https://ghcr.io/token?" + query, timeout=30) as response:
        token = json.load(response)["token"]
    request = urllib.request.Request(f"https://ghcr.io/v2/{repository}/manifests/latest", headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        manifest = json.load(response)
    platforms = {entry.get("platform", {}).get("architecture") for entry in manifest.get("manifests", []) if entry.get("platform", {}).get("os") == "linux"}
    if not {"amd64", "arm64"}.issubset(platforms):
        raise SystemExit("Published image must support linux/amd64 and linux/arm64.")
except (urllib.error.URLError, KeyError, ValueError):
    raise SystemExit("Image cannot be pulled anonymously. Open GitHub → profile → Packages → this package → Package settings → Change visibility → Public, then rerun this workflow. Do not publish a store pointing at a private image.")
print("Public image available for amd64 and arm64.")
