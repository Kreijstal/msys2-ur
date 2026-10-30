#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-libraries.sh PREPARED}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for spec in Microsoft.CodeAnalysis.Analyzers/Library.csproj Microsoft.CodeAnalysis.CSharp.Analyzers/Library.csproj Microsoft.CodeAnalysis.VisualBasic.Analyzers/Library.vbproj inventory-tool/Tool.csproj metadata-tool/Tool.csproj fixture-tool/Tool.csproj config-tool/Tool.csproj;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$spec")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
