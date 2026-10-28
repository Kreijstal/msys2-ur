#!/usr/bin/env python3
"""Hash tar payload paths, types, modes and bytes, excluding volatile metadata.

Gitiles assigns download-time mtimes to its archive entries. A raw archive
checksum therefore changes even for a fixed commit. This identity includes
every entry and its contents, but excludes timestamps and owner names/IDs.
"""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import tarfile


def tree_sha256(path):
    records = {}
    with tarfile.open(path) as archive:
        for entry in archive:
            name = PurePosixPath(entry.name)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"unsafe archive path: {entry.name}")
            name = name.as_posix()
            if name in records:
                raise ValueError(f"duplicate archive path: {name}")
            record = [name, entry.mode, entry.type.decode("ascii"), entry.linkname]
            if entry.isfile():
                with archive.extractfile(entry) as contents:
                    record.append(hashlib.file_digest(contents, "sha256").hexdigest())
            elif not (entry.isdir() or entry.issym() or entry.islnk()):
                raise ValueError(f"unsupported archive entry: {name}")
            records[name] = record
    payload = json.dumps([records[name] for name in sorted(records)],
                         ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def verify(path, expected):
    actual = tree_sha256(path)
    if actual != expected:
        raise ValueError(f"archive content checksum mismatch: {path}: {actual} != {expected}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    print(tree_sha256(args.archive))
