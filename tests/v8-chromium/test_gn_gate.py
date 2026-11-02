#!/usr/bin/env python3
"""Exercise the actual GN import and failure gate with temporary SDK fixtures."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_sdk
from test_sdk import ROOT


@unittest.skipUnless(shutil.which("gn"), "GN is not installed")
class GNGate(unittest.TestCase):
    def setUp(self):
        self.fixture = test_sdk.SDKGate()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.check()
        self.root = self.fixture.prefix / "consumer"
        (self.root / "v8/include").mkdir(parents=True)
        (self.root / "build").mkdir()
        self.flags = re.findall(r'^\+      (\w+) = \1$',
                                (ROOT / "mingw-w64-v8/018-sdk-interface.patch").read_text(), re.M)
        values = {key: False for key in self.flags}
        values.update(target_os="win", target_cpu="x64", v8_target_cpu="x64", v8_use_perfetto=True)
        self.fixture.manifest["private_defines"] = ["NDEBUG"]
        self.fixture.expected["private_defines"] = ["NDEBUG"]
        self.fixture.manifest["flags"] = values
        self.fixture.expected["flags"] = values.copy()
        self.fixture.check()
        (self.root / ".gn").write_text('buildconfig = "//build/BUILDCONFIG.gn"\nexec_script_allowlist = [ "//build/BUILDCONFIG.gn" ]\n')
        config = 'set_default_toolchain("//build:default")\nhost_os = "win"\nhost_cpu = "x64"\nis_mingw = true\n'
        config += '\n'.join(k + ' = ' + json.dumps(v) for k, v in values.items())
        config += '\ntemplate("component") { source_set(target_name) { forward_variables_from(invoker, "*") } }\n'
        (self.root / "build/BUILDCONFIG.gn").write_text(config)
        (self.root / "build/BUILD.gn").write_text('''toolchain("default") {
  tool("stamp") { command = "touch {{output}}" }
  tool("copy") { command = "cp {{source}} {{output}}" }
  tool("cxx") {
    command = "c++ -c {{source}} -o {{output}}"
    outputs = [ "{{target_out_dir}}/{{target_output_name}}.{{source_name_part}}.o" ]
  }
}
''')
        (self.root / "v8/include/v8-version.h").write_text('''#define V8_MAJOR_VERSION 14
#define V8_MINOR_VERSION 0
#define V8_BUILD_NUMBER 365
#define V8_PATCH_LEVEL 10
''')
        (self.root / "v8/BUILD.gn").write_text('''emit_builtins_as_inline_asm = false
v8_random_seed = "314159265"
v8_toolset_for_shell = "host"
is_DEBUG_defined = false
enabled_external_defines = [ "V8_ENABLE_SANDBOX" ]
disabled_external_defines = []
config("features") {
  defines = []
}
template("v8_source_set") {
  source_set(target_name) { forward_variables_from(invoker, "*") }
}
template("asm_to_inline_asm") {
}
v8_source_set("torque_generated_initializers") {
  sources = [ "forbidden-early-engine.cc" ]
  deps = [ ":implementation_only" ]
}
v8_source_set("v8_snapshot") {
  sources = [ "forbidden-bundled-engine.cc" ]
}
group("implementation_only") {
  assert(!emit_builtins_as_inline_asm && !is_DEBUG_defined &&
         v8_random_seed == "314159265" && v8_toolset_for_shell == "host")
}
''')
        perfetto = self.root / "third_party/perfetto"
        for directory in ("gn", "src/tracing/core"):
            (perfetto / directory).mkdir(parents=True)
        shutil.copytree(self.fixture.prefix / "share/v8/chromium-sdk/v8/third_party/perfetto/include",
                        perfetto / "include")
        (perfetto / "gn/perfetto.gni").write_text('# Tracing graph fixture only.\n')
        (perfetto / "gn/BUILD.gn").write_text('config("public_config") {}\n')
        (perfetto / "src/tracing/BUILD.gn").write_text('source_set("client_api") { sources = [ "forbidden-bundled-tracing.cc" ] }\n')
        (perfetto / "src/tracing/core/BUILD.gn").write_text('group("core") {}\n')
        (perfetto / "BUILD.gn").write_text('''import("gn/perfetto.gni")
  component("libperfetto") {
    public_configs = [ "gn:public_config" ]
    deps = [
      "src/tracing:client_api",
      "src/tracing/core",
    ]
    public_deps = [
    ]
  }

  # TODO(altimin): fixture of the following unrelated target.
''')
        (self.root / "BUILD.gn").write_text('group("all") { deps = [ "//v8:v8", "//v8:cppgc", "//v8:d8", "//third_party/perfetto:libperfetto" ] }\n')
        spec = importlib.util.spec_from_file_location("apply_system_v8", ROOT / "chromium-patches/v8/apply.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.installer = module
        self.original_build = (self.root / "v8/BUILD.gn").read_text()
        self.original_perfetto = (perfetto / "BUILD.gn").read_text()
        module.apply(self.root)

    def generate(self):
        manifest = self.fixture.manifest_path.as_posix()
        return subprocess.run(["gn", "gen", "out", "--args=" +
                               'use_system_v8=true system_v8_manifest=' + json.dumps(manifest)],
                              cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def test_external_graph_omits_bundled_implementation(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout)
        ninja = '\n'.join(p.read_text() for p in (self.root / "out").rglob("*.ninja"))
        self.assertNotIn("forbidden-bundled-engine.cc", ninja)
        self.assertNotIn("forbidden-early-engine.cc", ninja)
        self.assertNotIn("forbidden-bundled-tracing.cc", ninja)
        self.assertIn("libv8.dll", ninja)
        self.assertIn("libv8_libperfetto.dll", ninja)

    def test_bundled_branch_still_generates_without_sdk(self):
        (self.root / "BUILD.gn").write_text('group("all") { deps = [ "//v8:v8_snapshot", "//third_party/perfetto:libperfetto" ] }\n')
        result = subprocess.run(["gn", "gen", "out-bundled"], cwd=self.root, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(result.returncode, 0, result.stdout)
        ninja = '\n'.join(p.read_text() for p in (self.root / "out-bundled").rglob("*.ninja"))
        self.assertIn("forbidden-bundled-engine.cc", ninja)
        self.assertIn("forbidden-bundled-tracing.cc", ninja)

    def test_bundled_control_with_exported_feature_scope(self):
        original = self.original_build.replace('config("features") {', 'v8_sdk_internal_features = {')
        original = original.replace('template("v8_source_set") {',
            'config("features") {\n  forward_variables_from(v8_sdk_internal_features, "*")\n}\n'
            'template("v8_source_set") {')
        (self.root / "v8/BUILD.gn").write_text(original)
        (self.root / "third_party/perfetto/BUILD.gn").write_text(self.original_perfetto)
        self.installer.apply(self.root)
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_system_mode_skips_bundled_generator_settings(self):
        original = self.original_build.replace(
            'v8_random_seed = "314159265"',
            'v8_random_seed = read_file("//missing-bundled-generator-input")')
        (self.root / "v8/BUILD.gn").write_text(original)
        (self.root / "third_party/perfetto/BUILD.gn").write_text(self.original_perfetto)
        self.installer.apply(self.root)
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_gn_rejects_wrong_version(self):
        self.fixture.manifest["version"] = "14.6.0.0"
        self.fixture.manifest_path.write_text(json.dumps(self.fixture.manifest))
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version mismatch", result.stdout)

    def test_installer_preserves_script_allowlist(self):
        text = (self.root / ".gn").read_text()
        self.assertIn('exec_script_allowlist = [ "//build/BUILDCONFIG.gn" ]', text)
        self.assertIn('exec_script_allowlist += [ "//v8/BUILD.gn" ]', text)

    def test_gn_rejects_another_msys_runtime(self):
        with patch.dict(os.environ, {"MSYSTEM": "MINGW64"}):
            result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consumer shell runtime mismatch", result.stdout)

    def test_gn_rejects_wrong_feature(self):
        self.fixture.manifest["flags"]["v8_enable_sandbox"] = True
        self.fixture.manifest_path.write_text(json.dumps(self.fixture.manifest))
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("v8_enable_sandbox", result.stdout)

    def test_gn_rejects_mismatched_tracing_headers(self):
        header = self.root / "third_party/perfetto/include/perfetto/tracing/tracing.h"
        header.write_text("incompatible tracing interface\n")
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Perfetto public header mismatch", result.stdout)

    def test_gn_allows_consumer_only_perfetto_test_helpers(self):
        helpers = self.root / "third_party/perfetto/include/perfetto/test"
        helpers.mkdir(parents=True)
        (helpers / "traced_value_test_support.h").write_text("// Test harness only.\n")
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_gn_allows_registry_export_linkage_adjustment(self):
        relative = "perfetto/tracing/internal/track_event_macros.h"
        sdk_relative = "share/v8/chromium-sdk/v8/third_party/perfetto/include/" + relative
        sdk = self.fixture.prefix / sdk_relative
        sdk.parent.mkdir(parents=True, exist_ok=True)
        sdk.write_text("attrs extern const ::perfetto::internal::TrackEventCategoryRegistry  \\\n")
        self.fixture.manifest["sha256"][sdk_relative] = hashlib.sha256(sdk.read_bytes()).hexdigest()
        consumer = self.root / "third_party/perfetto/include" / relative
        consumer.parent.mkdir(parents=True, exist_ok=True)
        consumer.write_text("attrs const ::perfetto::internal::TrackEventCategoryRegistry         \\\n")
        self.fixture.check()
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_gn_rejects_external_icu_data_for_system_data_consumer(self):
        self.fixture.manifest["flags"]["icu_use_data_file"] = True
        self.fixture.manifest_path.write_text(json.dumps(self.fixture.manifest))
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("icu_use_data_file", result.stdout)

    def test_gn_rejects_non_mingw_toolchain(self):
        config = self.root / "build/BUILDCONFIG.gn"
        config.write_text(config.read_text().replace("is_mingw = true", "is_mingw = false"))
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a MinGW toolchain", result.stdout)


if __name__ == "__main__":
    unittest.main()
