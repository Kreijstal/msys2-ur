#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build-cdac.sh PREPARED_ROOT}" && pwd)
out="$root/cdac-bootstrap"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/tool/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$out/build.log" 2>&1
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/tool/bin/Release/net8.0/cdac-build-tool.dll")" compose --help >"$out/compose-help.log" 2>&1
