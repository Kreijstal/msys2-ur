#!/usr/bin/env python3
"""Validate an installed V8 SDK before GN accepts any external engine targets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_perfetto_headers(sdk_include, consumer_include):
    roots = [Path(sdk_include).resolve(), Path(consumer_include).resolve()]
    headers = [{p.relative_to(root).as_posix(): p for p in root.rglob("*")
                if p.is_file() and p.suffix in (".h", ".hh", ".hpp", ".inc")
                # Perfetto's testonly helper target belongs to the restored
                # content_shell harness, not the installed tracing runtime ABI.
                and not p.relative_to(root).as_posix().startswith("perfetto/test/")}
               for root in roots]
    if not headers[0] or headers[0].keys() != headers[1].keys():
        raise ValueError("consumer and SDK have different sets of Perfetto public headers")
    inputs = []
    for relative in sorted(headers[0]):
        contents = []
        for files in headers:
            path = files[relative]
            data = path.read_bytes().replace(b"\r\n", b"\n")
            if relative == "perfetto/tracing/internal/track_event_macros.h":
                # SDK patch 026 gives the exported const registry external
                # linkage. This changes DLL linkage, not the public layout.
                data = data.replace(b"attrs extern const ::perfetto::internal::TrackEventCategoryRegistry  \\",
                                    b"attrs const ::perfetto::internal::TrackEventCategoryRegistry         \\")
            contents.append(data)
            inputs.append(path.as_posix())
        if contents[0] != contents[1]:
            raise ValueError(f"Perfetto public header mismatch: {relative}")
    return inputs, len(headers[0])


def verify(manifest_path, expected, check_hashes=False):
    manifest_path = Path(manifest_path).resolve()
    manifest = read(manifest_path)
    if manifest.get("schema") != 1:
        raise ValueError("unsupported V8 SDK manifest schema")
    prefix = manifest_path.parent.parent.parent
    sdk_path = (prefix / manifest["sdk"]).resolve()
    if not sdk_path.is_relative_to(prefix):
        raise ValueError("SDK directory escapes install prefix")
    for key in ("version", "revision", "runtime"):
        if manifest.get(key) != expected[key]:
            raise ValueError(f"V8 {key} mismatch: SDK={manifest.get(key)!r}, consumer={expected[key]!r}")
    if manifest.get("heap_base_owner") != "v8" or manifest.get("cppgc_owner") != "v8":
        raise ValueError("this integration requires a single V8 DLL to own cppgc and heap-base")
    actual_flags, wanted_flags = manifest["flags"], expected["flags"]
    if set(actual_flags) != set(wanted_flags):
        raise ValueError("consumer and SDK describe different sets of V8 ABI flags")
    mismatches = [f"{key}: SDK={actual_flags[key]!r}, consumer={wanted_flags[key]!r}"
                  for key in sorted(actual_flags) if actual_flags[key] != wanted_flags[key]]
    if mismatches:
        raise ValueError("V8 ABI mismatch:\n" + "\n".join(mismatches))
    for key in ("public_defines", "disabled_defines", "private_defines"):
        actual_defines, wanted_defines = manifest[key], expected[key]
        if key == "private_defines":
            # Shared SDK consumers always use DLL TLS access, even when the
            # consumer itself is a non-component Chromium executable.
            actual_defines = [d for d in actual_defines if d != "V8_TLS_USED_IN_LIBRARY"]
            wanted_defines = [d for d in wanted_defines if d != "V8_TLS_USED_IN_LIBRARY"]
        if sorted(actual_defines) != sorted(wanted_defines):
            raise ValueError(f"V8 {key} mismatch")
    required_shared = {"USING_V8_SHARED", "USING_V8_SHARED_PRIVATE", "USING_V8_BASE_SHARED",
                       "USING_V8_PLATFORM_SHARED", "V8_TLS_USED_IN_LIBRARY"}
    if not required_shared.union(manifest["public_defines"]).issubset(manifest["shared_defines"]):
        raise ValueError("V8 SDK has incomplete shared-library import/TLS definitions")
    # No producer absolute paths: every recorded file must stay inside prefix.
    for relative, wanted_hash in manifest["sha256"].items():
        path = (prefix / relative).resolve()
        if not path.is_relative_to(prefix):
            raise ValueError(f"SDK file escapes install prefix: {relative}")
        if not path.is_file():
            raise ValueError(f"missing V8 SDK file: {path}")
        if check_hashes:
            with path.open("rb") as stream:
                actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual_hash != wanted_hash:
                raise ValueError(f"V8 SDK checksum mismatch: {relative}")
    required = [f"lib/lib{name}.dll.a" for name in ("v8", "v8_libbase", "v8_libplatform")]
    required += [f"bin/lib{name}.dll" for name in ("v8", "v8_libbase", "v8_libplatform")]
    required += ["lib/libv8_monolith.a", "share/v8/static-include/perfetto_build_flags.h"]
    if actual_flags.get("v8_use_perfetto"):
        required += ["lib/libv8_libperfetto.dll.a", "bin/libv8_libperfetto.dll"]
        for group, relative in (("libraries", "lib/libv8_libperfetto.dll.a"),
                                ("dlls", "bin/libv8_libperfetto.dll")):
            if manifest[group].get("v8_libperfetto") != relative:
                raise ValueError("V8 SDK is missing its shared Perfetto runtime interface")
    required += [f"bin/{name}.exe" for name in ("d8", "torque", "torque-language-server", "mksnapshot")]
    required += ["share/v8/chromium-sdk/v8/include/v8.h",
                 "share/v8/chromium-sdk/v8/include/cppgc/heap.h",
                 "share/v8/chromium-sdk/v8/src/heap/base/stack.h"]
    for relative in required:
        if relative not in manifest["sha256"]:
            raise ValueError(f"V8 SDK payload missing from manifest: {relative}")
    for group in ("tools", "libraries", "dlls"):
        for relative in manifest[group].values():
            if relative not in manifest["sha256"]:
                raise ValueError(f"untracked V8 SDK {group} path: {relative}")
    result = {"prefix": prefix.as_posix(),
              "sdk": sdk_path.as_posix(),
              "defines": manifest["shared_defines"],
              "private_defines": manifest["private_defines"]}
    for group in ("tools", "libraries", "dlls"):
        result[group] = {name.replace("-", "_"): (prefix / relative).as_posix()
                         for name, relative in manifest[group].items()}
    # GN file dependencies make upgrades regenerate the graph.
    if manifest.get("startup_blob") not in manifest["sha256"]:
        raise ValueError("missing matching default startup snapshot in V8 SDK")
    result["startup_blob"] = (prefix / manifest["startup_blob"]).as_posix()
    result["runtime_dlls"] = list(result["dlls"].values())
    result["inputs"] = [manifest_path.as_posix()]
    if actual_flags.get("v8_use_perfetto") and expected.get("perfetto_include"):
        headers, count = verify_perfetto_headers(sdk_path / "v8/third_party/perfetto/include",
                                                 expected["perfetto_include"])
        result["inputs"] += headers
        result["perfetto_header_count"] = count
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest")
    parser.add_argument("--pkg-config", default="pkg-config")
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--check-hashes", action="store_true")
    args = parser.parse_args()
    manifest = args.manifest
    if not manifest:
        manifest = subprocess.check_output([args.pkg_config, "--variable=manifest", "v8"], text=True).strip()
        if not manifest:
            raise ValueError("pkg-config v8 does not expose a Chromium SDK manifest")
    expected = read(args.expected)
    active_runtime = os.environ.get("MSYSTEM", "").lower()
    if active_runtime and active_runtime != expected["runtime"]:
        raise ValueError(f"consumer shell runtime mismatch: {active_runtime} != {expected['runtime']}")
    result = verify(manifest, expected, args.check_hashes)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"system V8: {error}", file=sys.stderr)
        sys.exit(1)
