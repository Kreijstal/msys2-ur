#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
bash "$here/../../mingw-w64-dotnet-mmi3/check-native-abi.sh" "$@"
