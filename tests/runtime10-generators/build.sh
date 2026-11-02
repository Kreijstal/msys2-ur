#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
for name in Microsoft.Interop.SourceGeneration Microsoft.Interop.LibraryImportGenerator Microsoft.Interop.ComInterfaceGenerator Microsoft.Interop.JavaScript.JSImportGenerator System.Text.Json.SourceGeneration System.Text.RegularExpressions.Generator; do
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$name/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$out/$name/build.log" 2>&1
 printf 'PASS original runtime10 netstandard2.0 generator: %s\n' "$name"
done
