#!/usr/bin/env bash
set -euo pipefail
output=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
export PATH=${MINGW_PREFIX}/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home") NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
for name in System.Private.ServiceModel System.Web.Services.Description contracts/System.ServiceModel.Primitives contracts/System.ServiceModel.Duplex contracts/System.ServiceModel.Security contracts/System.ServiceModel.Http contracts/System.ServiceModel.NetTcp; do
  ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$output/$name/build.csproj")" -c Release \
    --configfile "$(cygpath -m "$output/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
