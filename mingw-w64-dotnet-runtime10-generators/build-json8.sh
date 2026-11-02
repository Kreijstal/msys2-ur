#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-json8.sh PREPARED_JSON_ROOT SOURCE_COMPILER_HOST}" && pwd)
host=$(cd "${2:?missing SOURCE_COMPILER_HOST}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/System.Text.Json/Build.csproj")" -c Release \
 --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false \
 "-p:CscToolPath=$(cygpath -am "$host")" -p:CscToolExe=csc50.cmd -v:minimal >"$out/System.Text.Json/build.log" 2>&1
printf 'PASS original JSON10/net8 and its source dependencies with the source Compiler5/runtime9 host\n'
