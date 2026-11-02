#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: check.sh PREPARED_ROOT}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
/usr/bin/python3 "$here/audit-native.py" "$root" >"$root/audit-native.log" 2>&1
/usr/bin/python3 "$here/audit-source.py" "$root" >"$root/audit-source.log" 2>&1
bash "$here/check-eha.sh" "$root" "$root/eha-check" >"$root/eha-check.log" 2>&1
bash "$here/build-native-probe.sh" "$root" "$root/native-probe" >"$root/probe-build.log" 2>&1
/clang64/bin/python.exe "$(cygpath -am "$here/check-native.py")" "$(cygpath -am "$root")" "$(cygpath -am "$root/native-check")" "$(cygpath -am "$root/native-probe/native-jit-probe.exe")" >"$root/check-native.log" 2>&1
