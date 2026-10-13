import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

class StoreTests(unittest.TestCase):
    def test_store_configuration_uses_actual_repository_and_includes_ai(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            for name in ("docker-compose.yml", "store-config.json"):
                shutil.copy2(ROOT / name, fixture / name)
            (fixture / "scripts").mkdir()
            (fixture / "app/web").mkdir(parents=True)
            shutil.copy2(ROOT / "app/web/icon.svg", fixture / "app/web/icon.svg")
            shutil.copy2(ROOT / "scripts/prepare-github.py", fixture / "scripts/prepare-github.py")
            subprocess.run([sys.executable, str(fixture / "scripts/prepare-github.py"), "TestUser/FlowStore"], check=True, stdout=subprocess.DEVNULL)
            result = (fixture / "Apps/NoviFlowOSAssistant/docker-compose.yml").read_text()
            self.assertIn("ghcr.io/testuser/flowstore:latest", result)
            self.assertNotIn("YOUR_GITHUB_USER", result)
            self.assertNotIn("profiles:", result)
            self.assertNotIn("    build: .", result)
            self.assertIn("read_only: true", result)
            config = json.loads((fixture / "store-config.json").read_text())
            self.assertEqual(config["store_id"], "novi-testuser-flowstore")
            self.assertEqual(config["url"], "https://github.com/TestUser/FlowStore")

    def test_legacy_catalog_does_not_package_state_or_keys(self):
        spec = importlib.util.spec_from_file_location("legacy", ROOT / "scripts/build-legacy-store.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            (fixture / "Apps/Test").mkdir(parents=True)
            (fixture / "Apps/Test/docker-compose.yml").write_text("name: test")
            (fixture / "state").mkdir()
            (fixture / "state/access-key").write_text("private")
            for name in ("category-list.json", "featured-apps.json", "recommend-list.json"):
                (fixture / name).write_text("[]")
            archive = module.build(fixture, fixture / "dist/main.zip")
            with zipfile.ZipFile(archive) as zip:
                self.assertTrue(any(name.endswith("Apps/Test/docker-compose.yml") for name in zip.namelist()))
                self.assertFalse(any("access-key" in name for name in zip.namelist()))

if __name__ == "__main__":
    unittest.main()
