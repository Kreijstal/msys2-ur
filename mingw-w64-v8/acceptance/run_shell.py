#!/usr/bin/env python3
"""Run the same web test against bundled and system-V8 content_shell builds."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundled", type=Path, required=True)
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "content-shell-tests.json").unlink(missing_ok=True)
    test = (Path(__file__).resolve().parent / "engine.html").as_uri()
    results = {}
    for name, executable in (("bundled", args.bundled), ("system", args.system)):
        command = [str(executable.resolve()), "--run-web-tests", "--no-sandbox", "--disable-gpu",
                   "--js-flags=--expose-gc", test]
        result = subprocess.run(command, cwd=executable.resolve().parent, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        (evidence / (name + ".log")).write_text(result.stdout)
        if result.returncode or "PASS: JS async Wasm ICU DOM GC" not in result.stdout or "FAIL:" in result.stdout:
            raise ValueError(f"{name} content_shell failed; see {evidence / (name + '.log')}")
        results[name] = {"command": command, "returncode": result.returncode,
                         "result": "PASS: JS async Wasm ICU DOM GC"}
    (evidence / "content-shell-tests.json").write_text(json.dumps(results, indent=2) + "\n")
    print("PASS: bundled and system content_shell JS/async/Wasm/ICU/DOM/GC")


if __name__ == "__main__":
    main()
