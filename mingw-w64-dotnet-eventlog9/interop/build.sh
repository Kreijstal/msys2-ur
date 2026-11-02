#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?missing output}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
for name in Microsoft.Interop.SourceGeneration Microsoft.Interop.LibraryImportGenerator;do
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$name/$name.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal > "$out/$name/build.log" 2>&1
 printf 'PASS source9.0.11 NET8 generator bootstrap: %s\n' "$name"
done
