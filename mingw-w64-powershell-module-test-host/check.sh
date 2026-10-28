#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT [HOST_PAYLOAD]}
payload=${2:-/clang64/lib/dotnet/tools/powershell-module-test-host}
mkdir "$out";out=$(cd "$out" && pwd)
cp -R "$payload" "$out/relocated-host"
mkdir "$out/pester-owned"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 POWERSHELL_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT
host="$out/relocated-host/SourcePowerShell.ModuleHost.dll"
timeout 90 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$host")" "$(cygpath -am "$here/Smoke.ps1")"
timeout 120 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$host")" "$(cygpath -am "$here/ChildProcessSmoke.ps1")"
timeout 90 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$host")" "$(cygpath -am "$here/PesterSmoke.ps1")" \
  "$(cygpath -am "$out/relocated-host/Modules/Pester/Pester.psd1")" "$(cygpath -am "$out/pester-owned")"
printf "throw 'OwnedExpectedFailure'\n" > "$out/Negative.ps1"
if /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$host")" "$(cygpath -am "$out/Negative.ps1")" > "$out/negative.log" 2>&1;then
  echo 'negative script incorrectly succeeded' >&2;exit 1
fi
/usr/bin/grep -q OwnedExpectedFailure "$out/negative.log"
echo 'PASS relocated module host: original engine/cmdlets/compiler, source Pester/Gherkin and propagated terminating script failure'
