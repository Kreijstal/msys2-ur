#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec bash "$here/../../mingw-w64-dotnet-mmi3/check-mof-semantics.sh" "$@"
