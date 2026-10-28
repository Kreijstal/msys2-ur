#!/usr/bin/env python3
"""Extract pinned inputs using native Python (avoid MSYS/native xz pipe stalls)."""
import argparse
import json
from pathlib import Path, PurePosixPath
import tarfile
import os
import shutil
import subprocess

from archive_identity import verify


def assemble(root, source_name):
    source = root / source_name
    def junction(dest, target):
        if dest.is_junction():
            os.rmdir(dest)
        elif dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(dest).replace("/", "\\"), str(target).replace("/", "\\")], check=True)
    junction(source / "build", root / "build")
    for name in ("abseil-cpp", "jinja2", "markupsafe", "simdutf"):
        junction(source / "third_party" / name, root / name)
    for name in ("dragonbox", "fast_float", "fp16", "googletest", "highway"):
        junction(source / "third_party" / name / "src", root / name)
    junction(source / "tools/clang", root / "clang")
    for name in ("icu", "zlib"):
        dest = source / "third_party" / name
        dest.mkdir(parents=True, exist_ok=True)
        output = dest / "BUILD.gn"
        if output.is_symlink() or output.is_file():
            output.unlink()
        shutil.copy2(root / (name + ".gn"), output)
    (source / "third_party/icu/config.gni").write_text("icu_use_data_file = false\n")
    junction(source / "third_party/zlib/google", root / "zlib/google")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--qt-archive", required=True)
    parser.add_argument("--source-name", required=True)
    args = parser.parse_args()
    root = args.cache
    if args.assemble:
        assemble(root, args.source_name)
        return
    identities = json.loads((root / "source-trees.json").read_text())
    # Verify all dependency payloads before extracting or executing any input.
    for name, identity in identities.items():
        verify(root / name, identity)
        print(f"Verified {name} content tree", flush=True)
    vendor_prefix = args.qt_archive + "/src/3rdparty/chromium/"
    selected = ("v8/", "third_party/perfetto/", "third_party/protobuf/",
                "tools/protoc_wrapper/", "third_party/jsoncpp/source/", "chrome/VERSION")
    count = 0
    with tarfile.open(root / (args.qt_archive + ".tar.xz"), "r|xz") as archive:
        for member in archive:
            if not member.name.startswith(vendor_prefix):
                continue
            relative = member.name[len(vendor_prefix):]
            if relative in ("build/config/jumbo.gni", "build/config/merge_for_jumbo.py"):
                member.name = relative.removeprefix("build/")
                archive.extract(member, root / "qt-build-inputs", filter="data")
                continue
            if not relative.startswith(selected):
                continue
            if relative.startswith("v8/"):
                relative = relative[3:]
            # Tracing and protobuf stay below the standalone V8 root.
            if ".." in PurePosixPath(relative).parts or relative.startswith("/"):
                raise ValueError(f"unsafe archive path: {relative}")
            member.name = relative
            archive.extract(member, root / args.source_name, filter="data")
            count += 1
    print(f"Extracted {count} matched Qt/V8 inputs", flush=True)
    for dep in ("build", "clang", "abseil-cpp", "dragonbox", "fast_float", "fp16",
                "googletest", "highway", "jinja2", "markupsafe", "simdutf", "zlib"):
        archives = list(root.glob(dep + "-*.tar.gz"))
        if len(archives) != 1:
            raise ValueError(f"expected one pinned {dep} archive, got {archives}")
        with tarfile.open(archives[0]) as archive:
            archive.extractall(root / dep, filter="data")
        print(f"Extracted {dep}", flush=True)


if __name__ == "__main__":
    main()
