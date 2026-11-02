#!/usr/bin/env python3
"""Temporarily remove bundled V8 inputs while retaining its GN metadata."""
import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chromium", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    v8 = args.chromium.resolve() / "v8"
    backup = v8.parent / ".v8-system-sdk-validation"
    names = ("src", "include")
    if args.restore:
        for name in names:
            saved, original = backup / name, v8 / name
            if not saved.is_dir():
                raise ValueError(f"missing quarantined input: {saved}")
            shutil.rmtree(original)
            saved.rename(original)
        backup.rmdir()
    else:
        if backup.exists():
            raise ValueError(f"quarantine already exists: {backup}")
        if not all((v8 / name).is_dir() for name in names):
            raise ValueError("expected complete V8 source/include directories")
        backup.mkdir()
        for name in names:
            original, saved = v8 / name, backup / name
            original.rename(saved)
            original.mkdir()
            # These files describe targets; none are engine implementations.
            for path in saved.rglob("*"):
                if path.is_file() and path.suffix in (".gn", ".gni"):
                    target = original / path.relative_to(saved)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
    print("Restored bundled V8 inputs" if args.restore else "Quarantined bundled V8 inputs")


if __name__ == "__main__":
    main()
