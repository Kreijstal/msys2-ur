#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build-all.sh ARCHIVE_ROOT PREPARED}" && pwd)
out=$(cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
bash "$here/build.sh" "$out"
/usr/bin/python3 "$here/prepare-json8.py" "$root" "$root/json-runtime" "$out" >"$out/prepare-json.log" 2>&1
bash "$here/build-json8.sh" "$root/json-runtime" /clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap >"$out/build-json.log" 2>&1
