#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-libraries.sh PREPARED}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/StyleCop.Analyzers.CodeFixes/Library.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
