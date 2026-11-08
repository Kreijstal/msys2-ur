#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
cp "$here/"{provider.c,provider.def,native-client.c} "$out/"
/usr/bin/python3 - "$out" <<'PY'
from pathlib import Path
import json,sys,uuid
out=Path(sys.argv[1]);value=uuid.uuid4();fields=value.fields
initializer='{0x%08x,0x%04x,0x%04x,{' % fields[:3]+','.join('0x%02x'%x for x in value.bytes[8:])+'}}'
(out/'provider-guid.h').write_text('#define TEST_PROVIDER_CLSID '+initializer+'\n')
(out/'provider-id.json').write_text(json.dumps({'clsid':'{'+str(value).upper()+'}'})+'\n')
PY
"$MINGW_PREFIX/bin/clang" -std=c11 -Wall -Wextra -Werror -shared "$out/provider.c" "$out/provider.def" -lmi -o "$out/provider.dll"
"$MINGW_PREFIX/bin/clang" -std=c11 -Wall -Wextra -Werror -DPROVIDER_HOST -municode "$out/provider.c" -lmi -o "$out/provider-host.exe"
"$MINGW_PREFIX/bin/clang" -std=c11 -Wall -Wextra -Werror -municode "$out/native-client.c" -lmi -o "$out/native-client.exe"
bash "$here/build-consumer.sh" "$out/consumer"
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
set +e
/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "$(cygpath -am "$here/RunProvider.ps1")" -BuildRoot "$(cygpath -am "$out")" \
  -Dotnet "$(cygpath -am "$MINGW_PREFIX/lib/dotnet/dotnet.exe")" \
  -ManagedAssembly "$(cygpath -am "$out/consumer/bin/Release/net8.0/Check.dll")" \
  -PowerShell "$(cygpath -am "$MINGW_PREFIX/bin/pwsh.exe")"
result=$?
if [[ $result == 0 ]]; then
  /usr/bin/python3 "$here/validate-results.py" "$out" "$MINGW_PREFIX"
  result=$?
fi
printf '%s\n' "$result" > "$out/check-exit.txt"
exit "$result"
