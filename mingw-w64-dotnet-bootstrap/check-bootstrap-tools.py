#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the packaged Mono tool launchers against a relocated prefix tree."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

image, fixtures = map(Path, sys.argv[1:])
image = image.resolve()
# The UCRT64 seed is a dependency in the neighbouring prefix. A junction
# gives native Windows programs that same layout without copying the seed.
seed = Path(sys.executable).resolve().parents[2] / "ucrt64"
linked = image / "ucrt64"
if not linked.exists():
    subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(linked).replace("/", "\\"), str(seed).replace("/", "\\")], check=True, capture_output=True)
env = dict(os.environ, PATH=str(seed / "bin") + os.pathsep + os.environ["PATH"])
project = image / "bootstrap project"
project.mkdir(exist_ok=True)
source = project / "direct.cs"
source.write_text('class H { static void Main() { System.Console.WriteLine("bootstrap compiler OK"); } }\n', encoding="utf-8")
exe = project / "direct.exe"
subprocess.run([str(image / "clang64/bin/csc-bootstrap.exe"), "-nologo", "-out:" + str(exe), str(source)], check=True, cwd=project, env=env)
result = subprocess.check_output([str(seed / "bin/mono.exe"), str(exe)], text=True, encoding="utf-8-sig", env=env)
assert result.strip() == "bootstrap compiler OK", result
for file in fixtures.iterdir():
    if file.is_file():
        shutil.copy2(file, project / file.name)
subprocess.run([str(image / "clang64/bin/msbuild-bootstrap.exe"), "-nologo", "-m:1", "-nr:false", "-v:minimal", str(project / "hello.csproj")], check=True, cwd=project, env=env)
result = subprocess.check_output([str(seed / "bin/mono.exe"), str(project / "bin/Release/hello.exe")], text=True, encoding="utf-8-sig", env=env)
assert "Hello from MSBuild on Mono" in result and "(resource string via GenerateResource)" in result, result
print("PASS relocated bootstrap launchers: direct C# compiler and MSBuild with C# 12/resources")
