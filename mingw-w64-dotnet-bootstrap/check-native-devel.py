#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile and run consumers of the packaged hosting/Mono embedding files."""
from pathlib import Path
import shutil
import subprocess
import sys

image, compiler = map(Path, sys.argv[1:])
prefix = image.resolve() / "clang64"
work = image.resolve() / "native development check"
work.mkdir(exist_ok=True)

def build(name, source, include, library, dll):
    code = work / (name + ".c")
    code.write_text(source, encoding="utf-8")
    exe = work / (name + ".exe")
    subprocess.run([str(compiler), "-O2", "-Wall", "-Wextra", "-Werror", "-municode" if name == "hosting" else "-std=c11", "-I" + str(include), str(code), str(library), "-o", str(exe)], check=True)
    shutil.copy2(dll, work / dll.name)
    return exe

native = prefix / "lib/dotnet/hosting"
host = build("hosting", r'''
#include <nethost.h>
#include <stdio.h>
int wmain(int argc, wchar_t **argv) {
    if (argc != 2) return 2;
    char_t buffer[32768]; size_t length = 32768;
    struct get_hostfxr_parameters parameters = {sizeof(parameters), NULL, argv[1]};
    int rc = get_hostfxr_path(buffer, &length, &parameters);
    if (rc) return 1;
    wprintf(L"%ls\n", buffer);
    return 0;
}
''', prefix / "include/dotnet", native / "nethost.dll.a", native / "nethost.dll")
root = prefix / "lib/dotnet"
found = subprocess.check_output([str(host), str(root)], text=True)
expected = next((root / "host/fxr").glob("*/hostfxr.dll"))
assert Path(found.strip()).resolve() == expected.resolve(), (found, expected)
embedding = prefix / "lib/dotnet-mono/embedding"
mono = build("embedding", r'''
#include <mono/jit/jit.h>
#include <mono/utils/mono-publib.h>
#include <stdio.h>
int main(void) {
    char *info = mono_get_runtime_build_info();
    if (!info) return 1;
    puts(info);
    mono_free(info);
    return 0;
}
''', embedding / "include/mono-2.0", embedding / "lib/coreclr.import.lib", embedding / "lib/coreclr.dll")
version = subprocess.check_output([str(mono)], text=True)
assert "8.0.0" in version, version
print("PASS native development packages: nethost discovery and Mono embedding API")
