#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "${1:?usage: build-all.sh NEW_SOURCE_ROOT}" && pwd)
plan="$root/build-plan"
/clang64/bin/python.exe "$(cygpath -am "$here/prepare-source.py")" "$(cygpath -am "$root")"
/usr/bin/python3 "$here/prepare-version.py" "$root"
/usr/bin/python3 "$here/prepare.py" "$root" "$plan" --build-targets
bash "$here/evaluate.sh" "$root" "$plan"
/usr/bin/python3 "$here/prepare-tools.py" "$root" "$plan"
bash "$here/build-tools.sh" "$plan"
/usr/bin/python3 "$here/prepare-templating.py" "$root" "$plan"
/usr/bin/python3 "$here/regenerate-asn.py" "$root" "$plan" "$root/asn-check"
/usr/bin/python3 "$here/build.py" "$root" "$plan"
/usr/bin/python3 "$here/audit-source.py" "$root" "$plan"
