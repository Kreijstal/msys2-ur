#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check-powershell.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
bash "$here/build-powershell-fixture.sh" "$out/fixture"
"$MINGW_PREFIX/bin/clang" -std=c11 -shared -Wall -Wextra -Werror \
  "$here/../../mingw-w64-dotnet-sqlclient/localdb-driver.c" -o "$out/localdb-driver.dll"
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_ROOT_X64=$DOTNET_ROOT
for mode in STA MTA; do
  timeout -k 10 90 "$MINGW_PREFIX/bin/pwsh.exe" -NoLogo -NoProfile -NonInteractive \
    "-$mode" -ExecutionPolicy Bypass -File "$(cygpath -am "$here/PowerShellLocalDb.ps1")" \
    -Fixture "$(cygpath -am "$out/fixture/bin/Release/net8.0-windows/PowerShellLocalDbFixture.dll")" \
    -Driver "$(cygpath -am "$out/localdb-driver.dll")" \
    -SourceArchive "$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs/system.data.sqlclient.4.9.1.nupkg")"
  echo "PASS original installed PowerShell LocalDB checks in $mode"
done
