#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED}" && pwd)
mkdir -p "$out/../feed"
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for name in Microsoft.CodeAnalysis.Workspaces Microsoft.CodeAnalysis.CSharp.Workspaces;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/$name/Library.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
done
