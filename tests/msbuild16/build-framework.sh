#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-framework.sh PREPARED COMPILER44}" && pwd)
compiler=$(cd "${2:?missing csc4.4 directory}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache") MSBuildEnableWorkloadResolver=false DOTNET_CLI_TELEMETRY_OPTOUT=1
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/Framework.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false \
  -p:CscToolPath="$(cygpath -am "$compiler")" -p:CscToolExe=csc44.cmd -o "$(cygpath -am "$out/feed")" -v:minimal
