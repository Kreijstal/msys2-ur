#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$1" && pwd)
compiler=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT
export DOTNET_CLI_HOME=$(cygpath -am "$root/cli-home")
export NUGET_PACKAGES=$(cygpath -am "$root/cache")
export MSBuildEnableWorkloadResolver=false DOTNET_CLI_TELEMETRY_OPTOUT=1
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$root/Tasks.csproj")" -c Release --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am "$compiler")" -p:CscToolExe=csc44.cmd -o "$(cygpath -am "$root/feed")" -v:minimal
