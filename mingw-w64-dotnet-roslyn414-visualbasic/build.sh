#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh ROOT OUTPUT}" && pwd)
out=$(cd "${2:?missing OUTPUT}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
bash "$here/inputs/build-compiler.sh" "$out/roslyn-source" "$out/compiler" >"$out/compiler.log" 2>&1
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/workspaces/Microsoft.CodeAnalysis.VisualBasic.Workspaces/Library.vbproj")" -c Release \
 --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/feed")" -p:UseSharedCompilation=false -v:minimal >"$out/workspaces.log" 2>&1
printf 'PASS original VB4.14 compiler and Workspaces netstandard2.0 packages\n'

/usr/bin/python3 "$here/pack-meta.py" "$root" "$out" >"$out/meta.log" 2>&1
