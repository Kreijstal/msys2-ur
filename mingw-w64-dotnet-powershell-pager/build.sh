#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$root/cli-home") NUGET_PACKAGES=$(cygpath -am "$root/empty-packages")
printf '<configuration><packageSources><clear/></packageSources></configuration>\n' > "$root/NuGet.config"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe pack "$(cygpath -am "$root/src/Microsoft.PowerShell.Pager.csproj")" -c Release \
    --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -o "$(cygpath -am "$root/feed")" -v:minimal
