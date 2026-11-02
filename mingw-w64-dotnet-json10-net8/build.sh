#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
for name in System.Text.Encodings.Web System.IO.Pipelines System.Text.Json;do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/$name/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -o "$(cygpath -am "$out/feed")" -v:minimal >"$out/$name/build.log" 2>&1
 printf 'PASS original NET8 source package: %s\n' "$name"
done
