"""Pack the Apps catalog, not private application data, for legacy store clients."""
import argparse
from pathlib import Path
import zipfile

def build(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    prefix = Path("build/sysroot/var/lib/casaos/appstore/default.new")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((source / "Apps").rglob("*")):
            if file.is_file() and file.suffix in {".yml", ".yaml", ".svg", ".png", ".jpg"}:
                archive.write(file, str(prefix / file.relative_to(source)))
        for name in ("category-list.json", "featured-apps.json", "recommend-list.json"):
            archive.write(source / name, str(prefix / name))
    return destination

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=".")
    parser.add_argument("--output", default="dist/store/main.zip")
    args = parser.parse_args()
    print(build(args.source, args.output))
