#!/usr/bin/env python3
"""Install the resolved V8 interface and a relocatable Chromium development SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

SCHEMA = 2
TOOLS = ("d8", "torque", "torque-language-server", "mksnapshot")
LIBRARIES = ("v8", "v8_libbase", "v8_libplatform")
HEADER_DEPENDENCIES = ("abseil-cpp", "fp16", "dragonbox", "fast_float", "highway",
                       "simdutf", "zlib", "perfetto", "protobuf", "googletest",
                       "rapidhash-v8", "siphash", "utf8-decoder", "wasm-api")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def copy_headers(source, dest):
    # MSYS2 Python's iterdir() can retain mixed separators in WindowsPath's
    # cached spelling, which breaks relative_to() on its own glob children.
    source = Path(str(source).replace("\\", "/"))
    for path in source.rglob("*"):
        if path.is_file() and path.suffix in (".h", ".hh", ".hpp", ".inc", ".tq"):
            target = dest / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def install_headers(source, shared, dest, slot):
    sdk = dest / f"share/v8-{slot}/chromium-sdk"
    includes = dest / f"include/v8-{slot}"
    copy_headers(source / "include", includes)
    copy_headers(source / "include", sdk / "v8/include")
    copy_headers(shared / "gen/include", includes)
    copy_headers(shared / "gen/include", sdk / "v8/include")
    copy_headers(source / "src", sdk / "v8/src")
    # Production platform headers use Chromium's FRIEND_TEST forwarding header.
    copy_headers(source / "testing", sdk / "v8/testing")
    # Standalone V8's generated files sit at gen/, whereas Chromium nests
    # engine-generated inputs at gen/v8/. Preserve Chromium's include layout.
    for generated in (shared / "gen").iterdir():
        if generated.is_dir():
            relative = Path(generated.name) if generated.name in ("build", "third_party") else Path("v8") / generated.name
            copy_headers(generated, sdk / "gen" / relative)
        elif generated.suffix in (".h", ".hh", ".hpp", ".inc"):
            target = sdk / "gen/v8" / generated.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(generated, target)
    for name in HEADER_DEPENDENCIES:
        copy_headers(source / "third_party" / name, sdk / "v8/third_party" / name)
    for name in HEADER_DEPENDENCIES + ("jsoncpp",):
        dependency = source / "third_party" / name
        for pattern in ("LICENSE*", "COPYING*", "COPYRIGHT*"):
            for path in dependency.rglob(pattern):
                if path.is_file():
                    target = sdk / "v8/third_party" / name / path.relative_to(dependency)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)


def install(args):
    source, shared, static, dest = map(Path, (args.source, args.shared, args.static, args.dest))
    configs = [read_json(path / "v8-sdk-config.json") for path in (shared, static)]
    if configs[0] != configs[1]:
        raise ValueError("shared and monolithic builds have different engine interfaces")
    config = configs[0]
    # Every Chromium generation gets its own DLL names and directories, so
    # its consumers can coexist with the distribution's newer V8.
    slot, suffix = args.slot, "-" + args.slot
    share, libdir, tooldir = (dest / f"share/v8-{slot}", dest / f"lib/v8-{slot}",
                              dest / f"lib/v8-{slot}/bin")
    sdk = share / "chromium-sdk"
    for directory in (dest / "bin", dest / "lib/pkgconfig", sdk, tooldir):
        directory.mkdir(parents=True, exist_ok=True)
    # Include runtime components produced by matching tracing/protobuf targets.
    dlls = {path.name.removeprefix("lib").removesuffix(suffix + ".dll"): path
            for path in shared.glob(f"*{suffix}.dll")}
    imports = {path.name.removeprefix("lib").removesuffix(suffix + ".dll.a"): path
               for path in shared.glob(f"*{suffix}.dll.a")}
    for name in LIBRARIES:
        if name not in dlls or name not in imports:
            raise ValueError(f"missing required V8 output: lib{name}{suffix}.dll")
    for path in dlls.values():
        shutil.copy2(path, dest / "bin" / path.name)
    for path in imports.values():
        shutil.copy2(path, libdir / path.name)
    for name in TOOLS:
        shutil.copy2(shared / f"{name}.exe", tooldir / f"{name}.exe")
    shutil.copy2(static / "obj/libv8_monolith.a", libdir / "libv8_monolith.a")
    install_headers(source, shared, dest, slot)
    # Public Perfetto declarations derive dllimport from this generated header.
    # Static clients must see the real non-component build's configuration.
    static_config = share / "static-include/perfetto_build_flags.h"
    static_config.parent.mkdir(parents=True, exist_ok=True)
    static_input = static / "gen/third_party/perfetto/build_config/perfetto_build_flags.h"
    if "#define PERFETTO_BUILDFLAG_DEFINE_PERFETTO_COMPONENT_BUILD() (0)" not in static_input.read_text():
        raise ValueError("monolithic Perfetto configuration still enables component DLL imports")
    shutil.copy2(static_input, static_config)
    shutil.copy2(shared / "snapshot_blob.bin", share / "snapshot_blob.bin")
    # Static consumers must not inherit Windows dllimport annotations.
    public = config["public_defines"]
    shared_defines = public + ["USING_V8_SHARED", "USING_V8_SHARED_PRIVATE", "USING_V8_BASE_SHARED", "USING_V8_PLATFORM_SHARED", "V8_TLS_USED_IN_LIBRARY"]
    manifest = {
        "schema": SCHEMA,
        "version": args.version,
        "revision": args.revision,
        "chromium_version": "140.0.7339.225",
        "qt_chromium_revision": "5170777d28bee1ce92cc693a0dbf2ad01492e5cf",
        "qt_v8_tree": "5b48340636127f1d0016df90ecc945afd907dae3",
        "vendor_archive_sha256": args.vendor_sha256,
        "runtime": args.runtime,
        "flags": config["flags"],
        "public_defines": public,
        "private_defines": config["private_defines"],
        "disabled_defines": config["disabled_defines"],
        "shared_defines": shared_defines,
        "slot": slot,
        "sdk": f"share/v8-{slot}/chromium-sdk",
        "libraries": {name: f"lib/v8-{slot}/{path.name}" for name, path in imports.items()},
        "dlls": {name: f"bin/{path.name}" for name, path in dlls.items()},
        "tools": {name: f"lib/v8-{slot}/bin/{name}.exe" for name in TOOLS},
        "startup_blob": f"share/v8-{slot}/snapshot_blob.bin",
        "heap_base_owner": "v8",
        "cppgc_owner": "v8",
        "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
    }
    payload = sorted(p for p in sdk.rglob("*") if p.is_file())
    payload += sorted(p for p in (dest / f"include/v8-{slot}").rglob("*") if p.is_file())
    payload += [dest / p for group in ("libraries", "dlls", "tools") for p in manifest[group].values()]
    payload += [libdir / "libv8_monolith.a", dest / manifest["startup_blob"]]
    payload += [static_config]
    manifest["sha256"] = {p.relative_to(dest).as_posix(): digest(p) for p in payload}
    (share / "build-manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    for name in ("resolved-args.json", "interface.json", "cppgc-interface.json", "v8-sdk-config.json"):
        shutil.copy2(shared / name, share / name)
    shutil.copy2(static / "v8-sdk-config.json", share / "static-sdk-config.json")
    shutil.copy2(static / "link-libs.json", share / "static-link-libs.json")
    static_description = read_json(static / "link-libs.json")
    if len(static_description) != 1:
        raise ValueError("expected one monolithic V8 linker interface")
    static_libraries = next(iter(static_description.values()))["libs"]
    if not static_libraries:
        raise ValueError("monolithic V8 has no exported dependency libraries")
    static_link_flags = " ".join("-l" + name for name in static_libraries)
    for name, libs, requires, defines in (
        ("v8", f"-lv8{suffix}", "v8_libbase", shared_defines),
        ("v8_libbase", f"-lv8_libbase{suffix}", "", shared_defines),
        ("v8_libplatform", f"-lv8_libplatform{suffix}", "v8_libbase", shared_defines),
        ("cppgc", f"-lv8{suffix}", "v8 v8_libplatform", shared_defines),
        ("v8_monolith", "-lv8_monolith", "", public),
    ):
        requires = " ".join(f"{module}{suffix}" for module in requires.split())
        cflags = " ".join("-D" + value for value in defines)
        private_libs = static_link_flags if name == "v8_monolith" else ""
        profile_include = "-I${sharedir}/static-include " if name == "v8_monolith" else ""
        # Prefix is relative to the .pc file, including on native Windows.
        pc = f"""prefix=${{pcfiledir}}/../..
libdir=${{prefix}}/lib/v8-{slot}
includedir=${{prefix}}/include/v8-{slot}
sharedir=${{prefix}}/share/v8-{slot}
sdkdir=${{sharedir}}/chromium-sdk
manifest=${{sharedir}}/build-manifest.json
d8=${{libdir}}/bin/d8.exe
torque=${{libdir}}/bin/torque.exe
mksnapshot=${{libdir}}/bin/mksnapshot.exe
snapshot_blob=${{sharedir}}/snapshot_blob.bin

Name: {name}
Description: Chromium-matched V8 ({args.runtime})
Version: {args.version}
Requires: {requires}
Requires.private: icu-uc icu-i18n zlib
Libs: -L${{libdir}} {libs}
Libs.private: {private_libs}
Cflags: {profile_include}-I${{includedir}} -I${{sdkdir}}/v8/third_party/perfetto/include -I${{sdkdir}}/gen/third_party/perfetto -I${{sdkdir}}/gen/third_party/perfetto/build_config {cflags}
"""
        (dest / "lib/pkgconfig" / f"{name}{suffix}.pc").write_text(pc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    for name in ("source", "shared", "static", "dest", "version", "revision", "runtime", "vendor-sha256", "slot"):
        install_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.command == "install":
        install(args)


if __name__ == "__main__":
    main()
