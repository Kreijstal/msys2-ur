#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh PREPARED_ROOT JOBS}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
bash "$here/build-cdac.sh" "$root"
bash "$here/build-coreclr.sh" "$root" "${2:-2}"
