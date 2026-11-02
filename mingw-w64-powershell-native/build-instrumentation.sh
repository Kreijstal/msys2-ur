#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source_root=$(cd "${1:?usage: build-instrumentation.sh SOURCE SCHEMA WINMETA OUTPUT}" && pwd)
schema=$(cygpath -m "$2")
winmeta=$(cygpath -m "$3")
mkdir -p "$4"
output=$(cd "$4" && pwd)
/usr/bin/python3 "$here/prepare-manifest.py" \
  "$source_root/src/PowerShell.Core.Instrumentation/PowerShell.Core.Instrumentation.man" \
  "$output/PowerShell.Core.Instrumentation.man"
cd "$output"
event-manifest-compiler "$schema" "$winmeta" \
  "$(cygpath -m "$output/PowerShell.Core.Instrumentation.man")" PowerShell.Core.Instrumentation
cp "$source_root/src/PowerShell.Core.Instrumentation/version.rc" version.rc
printf '\n#include "version.rc"\n' >> PowerShell.Core.Instrumentation.rc
MSYS2_ARG_CONV_EXCL='*' llvm-rc /I "$(cygpath -m /clang64/include)" \
  /FO instrumentation.res PowerShell.Core.Instrumentation.rc
MSYS2_ARG_CONV_EXCL='*' lld-link /dll /noentry /nodefaultlib /machine:x64 \
  /out:PowerShell.Core.Instrumentation.dll instrumentation.res
