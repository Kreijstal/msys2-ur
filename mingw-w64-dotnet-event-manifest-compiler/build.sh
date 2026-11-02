#!/usr/bin/env bash
set -euo pipefail
output=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
export PATH=${MINGW_PREFIX}/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home")
export NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
cd "$output"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build Compiler.csproj -c Release \
  --configfile NuGet.config -p:UseSharedCompilation=false -v:minimal
