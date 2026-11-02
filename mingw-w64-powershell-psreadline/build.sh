#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh PREPARED_ROOT SOURCE_PAGER_FEED}" && pwd)
feed=$(cygpath -am "${2:-${MINGW_PREFIX}/lib/dotnet/library-packs}")
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$root/cli-home") NUGET_PACKAGES=$(cygpath -am "$root/empty-packages")
printf '<configuration><packageSources><clear/><add key="source-pager" value="%s"/></packageSources></configuration>\n' "$feed" > "$root/NuGet.config"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$root/PSReadLine/PSReadLine.csproj")" -c Release \
    --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$root/Polyfill/Polyfill.csproj")" -c Release \
    --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
