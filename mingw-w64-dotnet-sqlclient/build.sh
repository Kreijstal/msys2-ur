#!/usr/bin/env bash
set -euo pipefail
build=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
for role in implementation contract; do
  /clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/$role/build.csproj")" -c Release \
    --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
