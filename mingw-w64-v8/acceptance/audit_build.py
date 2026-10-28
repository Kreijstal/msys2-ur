#!/usr/bin/env python3
"""Reject a consumer that compiled bundled V8 or omitted the system import lib."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


def refers_to_import(text, library, out):
    """Resolve GNU linker paths, including paths relative to the Ninja output."""
    library = library.resolve()
    for argument in shlex.split(text.replace("\\", "/")):
        candidates = argument[4:].split(",") if argument.startswith("-Wl,") else [argument]
        for candidate in candidates:
            if candidate.rsplit("/", 1)[-1].casefold() != library.name.casefold():
                continue
            path = Path(candidate)
            if not path.is_absolute():
                path = out / path
            if path.resolve() == library:
                return True
    return False


def target_commands(ninja, out, target):
    path = out / "content-shell-compile-commands.json"
    with path.open("wb") as stream:
        subprocess.run([ninja, "-C", str(out), "-t", "compdb-targets", target],
                       stdout=stream, check=True)
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--ninja", default="ninja")
    args = parser.parse_args()
    chromium, out = args.chromium.resolve(), args.out.resolve()
    (out / "system-v8-audit.json").unlink(missing_ok=True)
    manifest = json.loads(args.manifest.read_text())
    prefix = args.manifest.resolve().parent.parent.parent
    bundled = chromium / "v8"
    # The GN-wide database also contains unrelated tools and test binaries.
    # Audit only the real dependency closure of the executable being accepted.
    commands = target_commands(args.ninja, out, "content_shell.exe")
    for directory in (bundled / "src", bundled / "include"):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in (".h", ".inc", ".cc", ".cpp", ".c", ".s", ".asm"):
                raise ValueError(f"bundled engine inputs are still accessible: {path}")
    forbidden = []
    tracing_muxers = []
    for entry in commands:
        file = Path(entry["file"])
        if not file.is_absolute():
            file = Path(entry["directory"]) / file
        file = file.resolve()
        if (file.is_relative_to(bundled) or file.is_relative_to(out / "gen/v8")) and file.suffix.lower() in (".cc", ".cpp", ".c", ".s", ".asm"):
            forbidden.append(str(file))
        if file.name == "tracing_muxer_impl.cc" and file.is_relative_to(chromium / "third_party/perfetto"):
            tracing_muxers.append(str(file))
    if forbidden:
        raise ValueError("consumer compiled bundled V8/cppgc/heap-base:\n" + "\n".join(forbidden))
    if tracing_muxers:
        raise ValueError("consumer compiled a second Perfetto tracing muxer:\n" + "\n".join(tracing_muxers))
    link_evidence = []
    wanted_import = prefix / manifest["libraries"]["v8"]
    executable = out / "content_shell.exe"
    command_path = out / "content-shell-link-command.txt"
    with command_path.open("wb") as stream:
        subprocess.run([args.ninja, "-C", str(out), "-t", "commands", "-s", executable.name],
                       stdout=stream, check=True)
    command = command_path.read_text(encoding="utf-8")
    command_uses_sdk = refers_to_import(command, wanted_import, out)
    retained = []
    for argument in shlex.split(command.replace("\\", "/")):
        if argument.startswith("@"):
            path = Path(argument[1:])
            if not path.is_absolute():
                path = out / path
            if not path.is_file():
                raise ValueError(f"linker response file was not retained: {path}; build with ninja -d keeprsp")
            retained.append(str(path))
            if refers_to_import(path.read_text(errors="replace"), wanted_import, out):
                link_evidence.append(str(path))
    if not retained:
        raise ValueError("content_shell linker command has no retained response file")
    if not command_uses_sdk and not link_evidence:
        raise ValueError("content_shell link does not use the installed libv8.dll.a")
    # The initial acceptance build is non-component so this imports V8 directly.
    pe = subprocess.check_output([args.objdump, "-p", str(executable)], text=True)
    imports = re.findall(r"DLL Name:\s*(\S+)", pe)
    if "libv8.dll" not in [name.lower() for name in imports]:
        raise ValueError("content_shell.exe does not import the packaged libv8.dll")
    for name, relative in manifest["dlls"].items():
        deployed = out / Path(relative).name
        if not deployed.is_file():
            raise ValueError(f"missing SDK runtime component: {deployed}")
        wanted = manifest["sha256"][relative]
        with deployed.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != wanted:
            raise ValueError(f"consumer runtime differs from packaged SDK: {deployed}")
    evidence = {"compiled_files": len(commands), "bundled_engine_files": 0,
                "bundled_tracing_muxer_files": 0,
                "link_response_files": link_evidence, "dll_imports": imports,
                "link_command_uses_sdk": command_uses_sdk,
                "retained_link_response_files": retained,
                "v8_version": manifest["version"], "revision": manifest["revision"],
                "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest()}
    (out / "system-v8-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
