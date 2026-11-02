#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove build-tree wrappers and make the Mono-hosted toolset relocatable."""
from pathlib import Path
import re
import shutil
import sys

root = Path(sys.argv[1])
for tools in [*root.glob("roslyn-*"), root / "msbuild-17.8.49"]:
    shutil.rmtree(tools / "bin", ignore_errors=True)
    (tools / ".pkgdir").unlink(missing_ok=True)
msbuild = root / "msbuild-17.8.49/tools"
config = msbuild / "MSBuild.exe.config"
text = config.read_text(encoding="utf-8-sig")
mono = "$([System.IO.Path]::GetFullPath('$([MSBuild]::GetToolsDirectory32())/../../../../../ucrt64/lib/mono"
values = {"TargetFrameworkRootPath": mono + "/xbuild-frameworks'))/",
          "MSBuildFrameworkToolsRoot": mono + "'))/"}
for name in ("MSBuildFrameworkToolsPath", "MSBuildFrameworkToolsPath32", "MSBuildFrameworkToolsPath64", "MSBuildFrameworkToolsPathArm64"):
    values[name] = mono + "/4.5'))/"
for name, value in values.items():
    pattern = r'(<property name="' + name + r'" value=")[^"]*("\s*/>)'
    text, count = re.subn(pattern, lambda m: m[1] + value + m[2], text)
    if not count:
        raise SystemExit("missing toolset property: " + name)
config.write_text(text, encoding="utf-8", newline="\n")
(msbuild / "Roslyn/csc-mono.cmd").write_text('@"%~dp0..\\..\\..\\..\\..\\..\\ucrt64\\bin\\mono.exe" "%~dp0csc.exe" %*\n', encoding="utf-8", newline="\r\n")
