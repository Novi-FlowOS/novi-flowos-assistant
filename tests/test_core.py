import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import core

SHA = "a" * 40

class CoreTests(unittest.TestCase):
    def test_device_dependency_graph_uses_pinned_commits(self):
        seen = []
        def fetch(url):
            seen.append(url)
            if "/branches/" in url:
                return {"commit": {"sha": SHA}}
            if "android_device_oneplus_fajita/" in url:
                return [{"repository": "android_device_oneplus_sdm845-common", "target_path": "device/oneplus/sdm845-common"}]
            if "android_device_oneplus_sdm845-common/" in url:
                return [{"repository": "android_kernel_oneplus_sdm845", "target_path": "kernel/oneplus/sdm845"}]
            return None
        result = core.research("oneplus", "fajita", "12L", fetch)
        self.assertEqual(len(result["evidence"]), 5)
        self.assertTrue(any(SHA + "/lineage.dependencies" in url for url in seen))
        self.assertFalse(result["build_ready"])

    def test_missing_device_branch_does_not_invent_dependencies(self):
        result = core.research("oneplus", "fajita", "16", lambda url: None)
        self.assertEqual(next(e for e in result["evidence"] if e["role"] == "device")["status"], "missing")
        self.assertFalse(any(e["role"] == "kernel" for e in result["evidence"]))

    def test_network_failure_is_not_missing_branch(self):
        def fetch(url):
            raise core.ResearchError("rate limit")
        with self.assertRaises(core.ResearchError):
            core.research("oneplus", "fajita", "12L", fetch)

    def test_dependency_path_traversal_rejected(self):
        def fetch(url):
            if "/branches/" in url:
                return {"commit": {"sha": SHA}}
            return [{"repository": "android_evil", "target_path": "device/../../secret"}]
        result = core.research("oneplus", "fajita", "12L", fetch)
        self.assertEqual(len(result["evidence"]), 3)
        self.assertTrue(any("Odrzucono" in gap for gap in result["gaps"]))

    def test_slug_blocks_url_and_shell_syntax(self):
        for text in ["../../etc", "fajita; reboot", "https://example.com", "", "a" * 65]:
            with self.assertRaises(ValueError):
                core.slug(text)

    def test_redaction_before_excerpt(self):
        text = "token=abcdef\n-----BEGIN PRIVATE KEY-----\nhidden\n-----END PRIVATE KEY-----\nFAILED: x\nerror: libncurses.so.5\nAuthorization: Bearer secret123\n"
        result = core.log_excerpt(text)
        for secret in ["abcdef", "hidden", "secret123"]:
            self.assertNotIn(secret, result)
        self.assertIn("libncurses.so.5", result)

    def test_last_error_excerpt_bounded(self):
        result = core.log_excerpt("prefix\n" * 2000 + "FAILED: actual\nerror: missing library\n" + "tail\n" * 100)
        self.assertIn("missing library", result)
        self.assertLessEqual(len(result), 12000)

    def test_known_hints_are_labelled_rules(self):
        self.assertIn("libncurses5", core.baseline_diagnosis("libncurses.so.5")[0]["cause"])

    def test_discovery_does_not_change_reference_project(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            device = path / "source/device/oneplus/fajita"
            device.mkdir(parents=True)
            (device / "BoardConfig.mk").write_text("original")
            (path / "logs").mkdir()
            (path / "logs/build.log").write_text("original log")
            result = core.discover(path, path / "ssd", path / "cdn")
            self.assertTrue(result["read_only"])
            self.assertIn({"vendor": "oneplus", "codename": "fajita"}, result["devices"])
            self.assertEqual((device / "BoardConfig.mk").read_text(), "original")
            self.assertEqual(result["logs"], ["build.log"])

    def test_model_response_and_no_tool_execution(self):
        captured = {}
        def fetch(url, **kwargs):
            captured.update(json.loads(kwargs["data"]))
            return {"message": {"content": json.dumps({"summary": "Przyczyna", "recommendations": ["Sprawdź bibliotekę"], "uncertainties": []})}}
        with patch("core.check_model_url", return_value="http://127.0.0.1:11434"):
            response = core.ai_answer("diagnose", {"log": "error"}, fetch=fetch)
        self.assertEqual(captured["keep_alive"], 0)
        self.assertFalse(captured["stream"])
        self.assertNotIn("tools", captured)
        self.assertTrue(response["advisory_only"])
        self.assertEqual(response["provider"], "ollama")

    def test_model_malformed_response_is_rejected(self):
        def fetch(url, **kwargs):
            return {"message": {"content": '{"recommendations":"run this"}'}}
        with patch("core.check_model_url", return_value="http://127.0.0.1:11434"):
            with self.assertRaises(core.ResearchError):
                core.ai_answer("diagnose", {}, fetch=fetch)

    def test_public_model_server_rejected(self):
        addresses = [(2, 1, 6, "", ("8.8.8.8", 11434))]
        with patch("socket.getaddrinfo", return_value=addresses):
            with self.assertRaises(ValueError):
                core.check_model_url("http://public.example:11434")

    def test_private_model_server_allowed(self):
        addresses = [(2, 1, 6, "", ("192.168.0.96", 11434))]
        with patch("socket.getaddrinfo", return_value=addresses):
            self.assertEqual(core.check_model_url("http://zima:11434"), "http://zima:11434")

    def test_dependency_branch_override_is_respected(self):
        seen=[]
        def fetch(url):
            seen.append(url)
            if "/branches/" in url:
                return {"commit": {"sha": SHA}}
            if "android_device_oneplus_fajita/" in url:
                return [{"repository": "android_kernel_example", "target_path": "kernel/example", "branch": "lineage-18.1"}]
            return None
        core.research("oneplus", "fajita", "12L", fetch)
        self.assertTrue(any("android_kernel_example/branches/lineage-18.1" in url for url in seen))

    def test_older_android_branches_are_checked(self):
        for android, branch in [("7.1", "lineage-14.1"), ("8.0", "lineage-15.0"), ("8.1", "lineage-15.1"), ("12.0", "lineage-19.0")]:
            result = core.research("oneplus", "fajita", android, lambda url: None)
            device = next(e for e in result["evidence"] if e["role"] == "device")
            self.assertEqual(device["branch"], branch)
            self.assertEqual(device["status"], "missing")

    def test_ai_phone_guess_must_have_a_real_repository(self):
        def ai(*args, **kwargs):
            return {"result": {"vendor": "example", "codename": "invented", "name": "Example Phone", "explanation": "test"}}
        result = core.identify_device("Unknown Phone", fetch=lambda url: None, identify=ai)
        self.assertEqual(result["devices"], [])

    def test_ai_phone_can_be_selected_after_repo_check(self):
        def ai(*args, **kwargs):
            return {"result": {"vendor": "google", "codename": "bluejay", "name": "Pixel 6a", "explanation": "test"}}
        result = core.identify_device("Google Pixel 6a", fetch=lambda url: {"name": "android_device_google_bluejay"}, identify=ai)
        self.assertEqual(result["devices"][0]["id"], "bluejay")

    def test_apk_manifest_identity(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app.apk"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("AndroidManifest.xml", '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="pl.novi.test" android:versionName="1.2"/>')
            self.assertEqual(core.apk_identity(path), {"package": "pl.novi.test", "version": "1.2"})
            result = core.application_list(Path(temp) / "missing", Path(temp))
            self.assertEqual(result["apps"][0]["package"], "pl.novi.test")

    def test_invalid_apk_is_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fake.apk"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("AndroidManifest.xml", '<manifest invalid')
            with self.assertRaises(ValueError):
                core.apk_identity(path)

if __name__ == "__main__":
    unittest.main()
