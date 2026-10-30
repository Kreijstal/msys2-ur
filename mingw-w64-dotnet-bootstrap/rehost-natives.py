#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace every native file of an extracted CLANG64 package tree.

usage: rehost-natives.py TREE... -- NAME=FILE... [PATH=FILE...]

A NAME=FILE argument replaces every file called NAME, a PATH=FILE argument
(PATH contains a slash, relative to a TREE) only that one.  Managed assemblies
(PE files with a CLR header) stay; any other .exe, .dll or .a that no
argument replaced is an error, so no CLANG64 native code is left over.
"""
from pathlib import Path
import shutil
import struct
import sys


def is_managed(path):
    data = path.read_bytes()
    if data[:2] != b"MZ":
        return False
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        return False
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    directories = opt + (112 if magic == 0x20B else 96)
    count = struct.unpack_from("<I", data, directories - 4)[0]
    if count <= 14:
        return False
    rva, size = struct.unpack_from("<II", data, directories + 14 * 8)
    return rva != 0 and size != 0


split = sys.argv.index("--")
trees = [Path(t) for t in sys.argv[1:split]]
by_name, by_path = {}, {}
for arg in sys.argv[split + 1:]:
    key, _, source = arg.partition("=")
    source = Path(source)
    if not source.is_file():
        sys.exit(f"missing replacement {source}")
    (by_path if "/" in key else by_name)[key] = source

used, replaced, left = set(), 0, []
for tree, path in sorted((t, p) for t in trees for p in t.rglob("*") if p.is_file()):
    rel = path.relative_to(tree).as_posix()
    source = by_path.get(rel) or by_name.get(path.name)
    if source:
        shutil.copyfile(source, path)
        used.add(rel if rel in by_path else path.name)
        replaced += 1
    elif path.suffix.lower() in (".exe", ".dll") and not is_managed(path):
        left.append(path.as_posix())
    elif path.suffix.lower() == ".a":
        left.append(path.as_posix())

unused = sorted((set(by_name) | set(by_path)) - used)
for rel in left:
    print(f"native file without a replacement: {rel}", file=sys.stderr)
for key in unused:
    print(f"replacement not used: {key}", file=sys.stderr)
if left or unused:
    sys.exit(1)
print(f"replaced {replaced} native files in {len(trees)} trees")
