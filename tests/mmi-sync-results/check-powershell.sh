#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check-powershell.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
bash "$here/build-powershell-fixture.sh" "$out/fixture"
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_ROOT_X64=$DOTNET_ROOT
export DOTNET_TieredCompilation=0
args=(); [[ ${2:-} != --baseline ]] || args+=(-Baseline)
for mode in STA MTA; do
  timeout -k 10 90 "$MINGW_PREFIX/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive \
    "-$mode" -ExecutionPolicy Bypass -File "$(cygpath -am "$here/PowerShellSyncResults.ps1")" \
    -Fixture "$(cygpath -am "$out/fixture/bin/Release/net8.0-windows/Microsoft.Management.Infrastructure.Tests.dll")" \
    -SourceArchive "$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs/microsoft.management.infrastructure.3.0.0.nupkg")" "${args[@]}"
  echo "PASS original installed PowerShell synchronous result ownership checks in $mode"
done
