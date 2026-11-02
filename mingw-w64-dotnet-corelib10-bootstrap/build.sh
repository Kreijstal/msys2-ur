#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh ARCHIVE_ROOT}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
gen="$root/corelib10-1/generator"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$gen/cli-home") NUGET_PACKAGES=$(cygpath -am "$gen/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$gen/Build.csproj")" -c Release --configfile "$(cygpath -am "$gen/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$gen/build.log" 2>&1
/usr/bin/python3 "$here/prepare-compile.py" "$root" >"$root/prepare-compile.log" 2>&1
bash "$here/build-corelib.sh" "$root"
/usr/bin/python3 "$here/rewrite.py" "$root" >"$root/rewrite.log" 2>&1
bash "$here/build-corerun.sh" "$root"
