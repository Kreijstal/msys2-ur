#!/usr/bin/env python3
"""Compile and run installed-SDK consumers outside the V8 producer directory."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


def run(command, *, cwd, env):
    print(shlex.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--pkg-config", default="pkg-config")
    parser.add_argument("--objdump", default="objdump")
    args = parser.parse_args()
    prefix, out = args.prefix.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "sdk-tests.json").unlink(missing_ok=True)
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = str(prefix / "lib/pkgconfig")
    env["PATH"] = str(prefix / "bin") + os.pathsep + env["PATH"]
    script_dir = Path(__file__).resolve().parent
    gate = script_dir.parents[1] / "chromium-patches/v8/verify_sdk.py"
    spec = importlib.util.spec_from_file_location("verify_sdk", gate)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    interface = json.loads((prefix / "share/v8/v8-sdk-config.json").read_text())
    expected = dict(interface, version="14.0.365.10",
                    revision="b7ed978e41b4bac7802b206404d0e2f3d09f31ac", runtime="ucrt64")
    sdk = verifier.verify(prefix / "share/v8/build-manifest.json", expected, check_hashes=True)
    (out / "sdk-validation.json").write_text(json.dumps(sdk, indent=2) + "\n")
    commands = []
    checks = []
    static_imports = {}
    for test, modules, static in (("embedder", ["v8", "v8_libplatform"], False),
                                  ("cppgc", ["cppgc"], False),
                                  ("heap-base", ["v8", "v8_libbase"], False),
                                  ("embedder", ["v8_monolith"], True),
                                  ("tracing", ["v8", "v8_libplatform"], False),
                                  ("tracing", ["v8_monolith"], True)):
        flags_cmd = [args.pkg_config] + (["--static"] if static else []) + ["--cflags", "--libs"] + modules
        flags = shlex.split(subprocess.check_output(flags_cmd, text=True, env=env))
        if test == "heap-base":
            flags += ["-I" + sdk["sdk"], "-I" + sdk["sdk"] + "/v8", "-I" + sdk["sdk"] + "/gen", "-I" + sdk["sdk"] + "/gen/v8"]
            flags += ["-D" + value for value in sdk["private_defines"]]
        if test == "tracing" and not static:
            flags += [sdk["libraries"]["v8_libperfetto"]]
        executable = out / (test + ("-static" if static else "") + ".exe")
        command = [args.cxx, "-std=c++20", script_dir / (test + ".cc"), "-o", executable] + flags
        commands.append(list(map(str, command)))
        run(command, cwd=out, env=env)
        if static:
            pe = subprocess.check_output([args.objdump, "-p", str(executable)], text=True, env=env)
            imports = re.findall(r"DLL Name:\s*(\S+)", pe)
            if any(name.lower().startswith("libv8") for name in imports):
                raise ValueError("monolithic consumer imported a V8 component DLL")
            static_imports[executable.stem] = imports
        invocation = [executable]
        if test == "tracing":
            invocation += [out / (executable.stem + ".pftrace")]
        run(invocation, cwd=out, env=env)
        checks.append(executable.stem)
    (out / "compile-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    (out / "static-dll-imports.json").write_text(json.dumps(static_imports, indent=2) + "\n")
    # The matched generator must generate actual consumer snapshot data.
    warmup = out / "snapshot.js"
    warmup.write_text("globalThis.sdkSnapshotAnswer = 42;\n")
    run([prefix / "bin/mksnapshot.exe", "--startup_blob", out / "consumer-snapshot.bin", warmup], cwd=out, env=env)
    if not (out / "consumer-snapshot.bin").stat().st_size:
        raise ValueError("mksnapshot produced an empty snapshot")
    checks.append("mksnapshot")
    report = {"passed": True, "checks": checks,
              "manifest_sha256": hashlib.sha256((prefix / "share/v8/build-manifest.json").read_bytes()).hexdigest(),
              "consumer_snapshot_sha256": hashlib.sha256((out / "consumer-snapshot.bin").read_bytes()).hexdigest()}
    (out / "sdk-tests.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: installed shared, static, cppgc, heap-base and snapshot SDK consumers", flush=True)


if __name__ == "__main__":
    main()
