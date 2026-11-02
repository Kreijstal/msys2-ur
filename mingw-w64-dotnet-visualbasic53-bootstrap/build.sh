#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?missing source root}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
bash "$here/vb-bootstrap-inputs/build-generators.sh" "$root/prepared/roslyn-source" "$root/vb-generators" > "$root/generators.log" 2>&1
/usr/bin/python3 "$here/build-net10-vb.py" "$root/prepared/roslyn-source" "$root/net10-plan" "$root/csharp" "$root/vb-generators" "$root/vb-build" > "$root/vb-build.log" 2>&1
/usr/bin/python3 "$here/build-net10-clients.py" "$root/prepared/roslyn-source" "$root/net10-plan" "$root/csharp" "$root/vb-build" "$root/clients" > "$root/clients.log" 2>&1
/usr/bin/python3 "$here/localize-net10-vb.py" "$root/prepared/roslyn-source" "$root/net10-plan" "$root/clients" "$root/vb-build" "$root/localized" > "$root/localized.log" 2>&1
