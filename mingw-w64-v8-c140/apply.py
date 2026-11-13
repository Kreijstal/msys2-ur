#!/usr/bin/env python3
"""Install the system-V8 GN branch without changing the bundled source branch."""
import argparse
from pathlib import Path
import re
import shutil

DECLARATION = '''
# MSYS2 system V8: producer and consumer must share an exact SDK interface.
declare_args() {
  use_system_v8 = false
  system_v8_manifest = ""
  system_v8_pkg_config = "pkg-config"
  system_v8_runtime = "ucrt64"
}
'''


def perfetto_branch(original):
    anchor = '  component("libperfetto") {'
    if original.count(anchor) != 1:
        raise ValueError("cannot locate the Chromium Perfetto runtime target")
    start = original.index(anchor)
    end = original.index('\n  # TODO(altimin):', start)
    bundled = original[start:end]
    shared = bundled.replace('component("libperfetto")', 'group("libperfetto")', 1)
    # The SDK's genuine tracing DLL already contains the client/muxer and core.
    # Keep Chromium's other processor, IPC, JSON and public-header dependencies.
    for label in ('src/tracing:client_api', 'src/tracing/core'):
        line = f'      "{label}",\n'
        if shared.count(line) != 1:
            raise ValueError(f"unexpected Perfetto runtime dependency: {label}")
        shared = shared.replace(line, '')
    shared = re.sub(r'^    configs [+-]= .*\n', '', shared, flags=re.M)
    shared = shared.replace('    public_deps = [\n',
                            '    public_deps = [\n      "//v8:system_v8_perfetto",\n', 1)
    result = original[:start] + '  if (use_system_v8) {\n' + shared
    result += '  } else {\n' + bundled + '  }\n' + original[end:]
    import_line = 'import("gn/perfetto.gni")'
    if result.count(import_line) != 1:
        raise ValueError("cannot locate the Perfetto argument import")
    return result.replace(import_line,
                          import_line + '\nimport("//v8/system_v8/args.gni")', 1)


def blink_branch(original):
    # Blink's public headers include cppgc unconditionally (nogncheck). Bundled
    # V8 is reachable from the source root; the installed SDK is not.
    anchor = '    "//v8:v8_headers",\n  ]\n}\n'
    if original.count(anchor) != 1:
        raise ValueError("cannot locate blink_headers' V8 dependency")
    result = original.replace(anchor, anchor[:-2] + '''
  if (use_system_v8) {
    public_deps += [ "//v8:v8_headers" ]
  }
}
''', 1)
    return 'import("//v8/system_v8/args.gni")\n' + result


def apply(chromium):
    chromium = Path(chromium).resolve()
    v8 = chromium / "v8"
    build = v8 / "BUILD.gn"
    original = build.read_text()
    if '# BEGIN MSYS2 SYSTEM V8' in original:
        raise ValueError("system-V8 branch is already installed; use a fresh source tree")
    header = (v8 / "include/v8-version.h").read_text()
    values = [re.search(r"#define " + name + r"\s+(\d+)", header).group(1)
              for name in ("V8_MAJOR_VERSION", "V8_MINOR_VERSION", "V8_BUILD_NUMBER", "V8_PATCH_LEVEL")]
    if ".".join(values) != "14.0.365.10":
        raise ValueError("this patchset requires V8 14.0.365.10")
    anchor = 'template("asm_to_inline_asm") {'
    if original.count(anchor) != 1:
        raise ValueError("cannot locate V8 implementation/generator boundary")
    feature_start = original.index('config("features") {')
    feature_end = original.index('\n}\n', feature_start) + 2
    feature_body = original[feature_start + len('config("features") {'):feature_end - 1]
    if 'v8_sdk_internal_features = {' in original:
        # A bundled control may already export the resolved SDK interface.
        # Reuse its scope rather than wrapping the forwarding config again.
        if feature_body.strip() != 'forward_variables_from(v8_sdk_internal_features, "*")':
            raise ValueError("existing SDK feature scope has an unexpected forwarding config")
    else:
        original = (original[:feature_start] + 'v8_sdk_internal_features = {' + feature_body +
                    '}\nconfig("features") {\n  forward_variables_from(v8_sdk_internal_features, "*")\n}' +
                    original[feature_end:])
    preamble, implementation = original.split(anchor)
    # These locals configure bundled generators, not the resolved engine ABI.
    # GN rejects their unused assignments when that implementation is skipped.
    for name in ("emit_builtins_as_inline_asm", "v8_random_seed",
                 "v8_toolset_for_shell", "is_DEBUG_defined"):
        preamble, count = re.subn(
            r"^" + name + r" = [^\n]+\n",
            lambda match: "if (!use_system_v8) {\n  " + match.group() + "}\n",
            preamble, flags=re.M)
        if count != 1:
            raise ValueError(f"cannot locate bundled generator setting: {name}")
    targets = (Path(__file__).parent / "system_v8_targets.gni").read_text()
    perfetto = chromium / "third_party/perfetto/BUILD.gn"
    perfetto_result = perfetto_branch(perfetto.read_text())
    blink = chromium / "third_party/blink/public/BUILD.gn"
    blink_result = blink_branch(blink.read_text()) if blink.exists() else None
    result = 'import("system_v8/args.gni")\n' + preamble + "if (use_system_v8) {\n"
    # GN imports have isolated scopes. Inline this maintained fragment so the
    # check reads V8's resolved local values, including automatic cppgc flags.
    result += "# BEGIN MSYS2 SYSTEM V8\n" + targets + "# END MSYS2 SYSTEM V8\n"
    result += "} else {\n" + anchor + implementation + "\n}\n"
    # Copy before modifying the build entry point. The bundled implementation
    # remains byte-for-byte present inside the false branch.
    target = v8 / "system_v8"
    target.mkdir(exist_ok=True)
    (target / "args.gni").write_text(DECLARATION)
    for name in ("verify_sdk.py", "system_v8_targets.gni"):
        shutil.copy2(Path(__file__).parent / name, target / name)
    dotfile = chromium / ".gn"
    dotfile_text = dotfile.read_text()
    for variable in ("exec_script_allowlist", "exec_script_whitelist"):
        if re.search(r"^\s*" + variable + r"\s*=", dotfile_text, re.M):
            dotfile_text += '\n' + variable + ' += [ "//v8/BUILD.gn" ]\n'
            dotfile.write_text(dotfile_text)
            break
    build.write_text(result)
    perfetto.write_text(perfetto_result)
    if blink_result is not None:
        blink.write_text(blink_result)


def hide_bundled(chromium):
    """Remove bundled V8 sources and headers, keeping only what GN reads.

    Consumers must compile against the SDK's headers: Chromium sources include
    v8/include from the source root, which would otherwise win.
    """
    v8 = Path(chromium).resolve() / "v8"
    for path in sorted(v8.rglob("*"), reverse=True):
        relative = path.relative_to(v8).as_posix()
        if path.is_dir():
            if not any(path.iterdir()):
                path.rmdir()
            continue
        keep = (path.suffix in (".gn", ".gni") or relative.startswith("system_v8/")
                # Blink's DevTools protocol build reads V8's schema and baselines.
                or (relative.startswith("include/js_protocol")))
        if not keep:
            path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chromium", type=Path)
    parser.add_argument("--hide-bundled", action="store_true",
                        help="also remove bundled V8 sources and headers")
    args = parser.parse_args()
    apply(args.chromium)
    if args.hide_bundled:
        hide_bundled(args.chromium)
