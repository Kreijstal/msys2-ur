#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check-powershell.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
bash "$here/build-powershell-fixture.sh" "$out/fixture"
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_ROOT_X64=$DOTNET_ROOT
for mode in STA MTA; do
  timeout -k 10 180 "$MINGW_PREFIX/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive \
    "-$mode" -ExecutionPolicy Bypass -File "$(cygpath -am "$here/PowerShellMarsCancel.ps1")" \
    -Fixture "$(cygpath -am "$out/fixture/bin/Release/net8.0-windows/PowerShellMarsCancelFixture.dll")" \
    -SourceArchive "$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs/system.data.sqlclient.4.9.1.nupkg")"
  echo "PASS original installed PowerShell MARS cancellation/TLS checks in $mode"
done
