#!/usr/bin/env python3
"""Negative tests for the system SDK compatibility gate (no engine build needed)."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verify_sdk", ROOT / "chromium-patches/v8/verify_sdk.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class SDKGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.prefix = Path(self.temp.name)
        self.manifest_path = self.prefix / "share/v8/build-manifest.json"
        self.manifest_path.parent.mkdir(parents=True)
        self.expected = {"version": "14.0.365.10", "revision": "b7ed978e41b4bac7802b206404d0e2f3d09f31ac",
                         "runtime": "ucrt64", "flags": {"v8_enable_sandbox": True},
                         "public_defines": ["V8_ENABLE_SANDBOX"], "disabled_defines": [], "private_defines": []}
        self.manifest = copy.deepcopy(self.expected)
        self.manifest.update(schema=1, sdk="share/v8/chromium-sdk", heap_base_owner="v8", cppgc_owner="v8",
                             startup_blob="share/v8/snapshot_blob.bin", shared_defines=["V8_ENABLE_SANDBOX", "USING_V8_SHARED", "USING_V8_SHARED_PRIVATE",
                                             "USING_V8_BASE_SHARED", "USING_V8_PLATFORM_SHARED", "V8_TLS_USED_IN_LIBRARY"], sha256={})
        self.manifest["libraries"] = {n: f"lib/lib{n}.dll.a" for n in ("v8", "v8_libbase", "v8_libplatform", "v8_libperfetto")}
        self.manifest["dlls"] = {n: f"bin/lib{n}.dll" for n in self.manifest["libraries"]}
        self.manifest["tools"] = {n: f"bin/{n}.exe" for n in ("d8", "torque", "torque-language-server", "mksnapshot")}
        files = ["share/v8/snapshot_blob.bin", "lib/libv8_monolith.a",
                 "share/v8/static-include/perfetto_build_flags.h",
                 "share/v8/chromium-sdk/v8/include/v8.h",
                 "share/v8/chromium-sdk/v8/include/cppgc/heap.h",
                 "share/v8/chromium-sdk/v8/src/heap/base/stack.h",
                 "share/v8/chromium-sdk/v8/third_party/perfetto/include/perfetto/tracing/tracing.h"]
        files += [p for group in ("libraries", "dlls", "tools") for p in self.manifest[group].values()]
        for relative in files:
            path = self.prefix / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture for compatibility gate only\n")
            self.manifest["sha256"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()

    def check(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        return verifier.verify(self.manifest_path, self.expected, check_hashes=True)

    def test_matching_relocated_sdk(self):
        result = self.check()
        self.assertEqual(result["tools"]["torque_language_server"], str(self.prefix / "bin/torque-language-server.exe"))

    def test_wrong_version(self):
        self.manifest["version"] = "14.6.202.26"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            self.check()

    def test_wrong_runtime(self):
        self.manifest["runtime"] = "clang64"
        with self.assertRaisesRegex(ValueError, "runtime mismatch"):
            self.check()

    def test_wrong_feature(self):
        self.manifest["flags"]["v8_enable_sandbox"] = False
        with self.assertRaisesRegex(ValueError, "v8_enable_sandbox"):
            self.check()

    def test_missing_feature(self):
        self.manifest["flags"].clear()
        with self.assertRaisesRegex(ValueError, "different sets"):
            self.check()

    def test_wrong_public_defines(self):
        self.manifest["public_defines"] = []
        with self.assertRaisesRegex(ValueError, "public_defines mismatch"):
            self.check()

    def test_dll_tls_linkage_is_explicit(self):
        self.manifest["shared_defines"].remove("V8_TLS_USED_IN_LIBRARY")
        with self.assertRaisesRegex(ValueError, "import/TLS"):
            self.check()

    def test_qt_tls_linkage_is_canonicalized(self):
        self.expected["private_defines"] = ["V8_TLS_USED_IN_LIBRARY"]
        self.check()

    def test_wrong_private_feature(self):
        self.manifest["private_defines"] = ["V8_JITLESS"]
        with self.assertRaisesRegex(ValueError, "private_defines mismatch"):
            self.check()

    def test_missing_generator(self):
        (self.prefix / "bin/mksnapshot.exe").unlink()
        with self.assertRaisesRegex(ValueError, "missing V8 SDK file"):
            self.check()

    def test_missing_shared_tracing_runtime(self):
        self.manifest["flags"]["v8_use_perfetto"] = True
        self.expected["flags"]["v8_use_perfetto"] = True
        del self.manifest["libraries"]["v8_libperfetto"]
        with self.assertRaisesRegex(ValueError, "shared Perfetto runtime interface"):
            self.check()

    def test_modified_library(self):
        (self.prefix / "bin/libv8.dll").write_bytes(b"wrong engine")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.check()

    def test_manifest_path_escape(self):
        self.manifest["sha256"]["../outside"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "escapes install prefix"):
            self.check()

    def test_sdk_directory_escape(self):
        self.manifest["sdk"] = "../outside"
        with self.assertRaisesRegex(ValueError, "SDK directory escapes install prefix"):
            self.check()

    def test_duplicate_gc_owner(self):
        self.manifest["cppgc_owner"] = "cppgc"
        with self.assertRaisesRegex(ValueError, "single V8 DLL"):
            self.check()

    def test_payload_removed_from_manifest(self):
        del self.manifest["sha256"]["bin/libv8.dll"]
        with self.assertRaisesRegex(ValueError, "payload missing"):
            self.check()


if __name__ == "__main__":
    unittest.main()
