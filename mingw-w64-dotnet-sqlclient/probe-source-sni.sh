#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: probe-source-sni.sh PINNED_SOURCE PORT_BUILD NEW_OUTPUT [--mars-only]}" && pwd)
build=$(cd "${2:?missing port build}" && pwd)
out=${3:?missing new output}
/usr/bin/python3 "$here/prepare-tds.py" "$source" "$out" "$build"
out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
unset 'System.Data.SqlClient.UseManagedSNIOnWindows'
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Probe.csproj")" -c Release \
  --configfile "$(cygpath -am "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
cd "$out"
timeout 120 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0-windows/Probe.dll")" "${@:4}"
