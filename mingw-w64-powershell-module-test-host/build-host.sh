#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "${1:?usage: build-host.sh PREPARED_CORE_ROOT NEW_HOST_OUTPUT}" && pwd)
out=${2:?missing host output}
/usr/bin/python3 "$here/prepare-host.py" "$root/PowerShell-7.4.20" "$out"
out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$root/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/ModuleHost.csproj")" -c Release \
  --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 "$here/stage-runtime.py" "$root/PowerShell-7.4.20" "$out/bin/Release/net8.0" \
  ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0
