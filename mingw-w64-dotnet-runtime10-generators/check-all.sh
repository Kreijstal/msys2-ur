#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: check-all.sh ARCHIVE_ROOT PREPARED}" && pwd)
out=$(cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
/usr/bin/python3 "$here/check.py" "$root" "$out" "$root/consumer" "$root/json-runtime" >"$out/consumer.log" 2>&1
/usr/bin/python3 "$here/audit.py" "$root" "$out" "$root/consumer" >"$out/audit.log" 2>&1
/usr/bin/python3 "$here/audit-json8.py" "$root" "$root/json-runtime" "$out" /clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap >"$out/json-audit.log" 2>&1
/usr/bin/python3 "$here/stage.py" "$root" "$out" "$root/stage" >"$out/stage.log" 2>&1
