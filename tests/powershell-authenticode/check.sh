#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export PATH=/clang64/bin:/usr/bin:$PATH
bash "$here/../../mingw-w64-dotnet-security-extensions/generate-fixtures.sh" "$out/fixtures" > "$out/fixtures.log" 2>&1
for apartment in STA MTA; do
  env MSYS2_ARG_CONV_EXCL='*' timeout -k 10 120 /clang64/bin/pwsh.exe \
    -NoLogo -NoProfile -NonInteractive -"$apartment" -ExecutionPolicy Bypass \
    -File "$(cygpath -am "$here/Check.ps1")" -Fixtures "$(cygpath -am "$out/fixtures")" \
    -Feed "$(cygpath -am /clang64/lib/dotnet/library-packs)" \
    -Output "$(cygpath -am "$out/$apartment.json")" > "$out/$apartment.log" 2>&1
  cat "$out/$apartment.log"
done
