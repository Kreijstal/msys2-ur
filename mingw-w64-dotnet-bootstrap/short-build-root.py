#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create a private short Windows junction for legacy compiler path limits."""
from pathlib import Path
import subprocess
import sys

target, link = map(Path, sys.argv[1:])
if not target.is_dir():
    raise SystemExit("missing private bootstrap build tree: " + str(target))
result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link).replace("/", "\\"), str(target).replace("/", "\\")], capture_output=True)
if result.returncode:
    raise SystemExit("cannot create build junction: " + repr(result.stderr))
