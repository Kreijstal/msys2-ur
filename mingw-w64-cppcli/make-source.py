#!/usr/bin/env python3
"""Export the pinned, unpublished bootstrap sources for makepkg."""
import argparse
import gzip
from pathlib import Path
import subprocess

COMMIT = "3cbf21078968e2290a54ab093392b4dfeb1c6f1f"
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("repo", nargs="?", type=Path, default=Path(__file__).resolve().parents[2] / "dotnet-bootstrap")
p.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
target = a.output / ("dotnet-bootstrap-" + COMMIT + ".tar.gz")
# GzipFile fixes the OS header across Python/MSYS2 versions as well as mtime.
with target.open("wb") as output, gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as compressed:
    proc = subprocess.Popen(["git", "-C", str(a.repo), "archive", "--format=tar",
                             "--prefix=dotnet-bootstrap-" + COMMIT + "/", COMMIT], stdout=subprocess.PIPE)
    try:
        while chunk := proc.stdout.read(1024 * 1024):
            compressed.write(chunk)
        if proc.wait() != 0:
            raise SystemExit("git archive failed")
    finally:
        proc.stdout.close()
print(target)
