#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?ARCHIVE_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$root/build/cli-home") NUGET_PACKAGES=$(cygpath -am "$root/build/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$root/build/Build.csproj")" -c Release --configfile "$(cygpath -am "$root/build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$root/build.log" 2>&1
