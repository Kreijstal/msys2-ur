#!/usr/bin/env python3
"""Restore test-harness files omitted from Qt's pruned Chromium distribution."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import tarfile
import shutil
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mingw-w64-v8"))
from archive_identity import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()
    root = args.chromium.resolve()
    args.cache.mkdir(parents=True, exist_ok=True)
    specifications = json.loads((Path(__file__).parent / "control-inputs.json").read_text())
    for spec in specifications:
        if args.only and spec["path"] not in args.only:
            continue
        archive = args.cache / spec["file"]
        if not archive.exists():
            temporary = archive.with_name(archive.name + ".part")
            with urllib.request.urlopen(spec["url"], timeout=120) as response, temporary.open("wb") as output:
                if spec.get("encoding") == "base64":
                    output.write(base64.b64decode(response.read()))
                else:
                    shutil.copyfileobj(response, output)
            try:
                check_input(temporary, spec)
            except ValueError:
                temporary.unlink()
                raise
            temporary.replace(archive)
        check_input(archive, spec)
        destination = root / spec["path"]
        if spec.get("kind") == "file":
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archive, destination)
            print(f"{spec['path']}: file restored", flush=True)
            continue
        destination = destination.resolve()
        added = 0
        with tarfile.open(archive) as source:
            for member in source:
                target = (destination / member.name).resolve()
                if not target.is_relative_to(destination):
                    raise ValueError(f"archive path escapes destination: {member.name}")
                # Preserve all existing Qt security and MinGW port changes.
                if not target.exists():
                    source.extract(member, destination, filter="data")
                    if member.isfile():
                        added += 1
        print(f"{spec['path']}: restored {added} files", flush=True)


def check_input(path, spec):
    if "tree_sha256" in spec:
        verify(path, spec["tree_sha256"])
    else:
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != spec["sha256"]:
            raise ValueError(f"checksum mismatch: {path}")


if __name__ == "__main__":
    main()
