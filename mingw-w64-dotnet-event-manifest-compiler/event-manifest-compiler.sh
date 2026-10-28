#!/usr/bin/env bash
set -euo pipefail
prefix=$(cd "$(dirname "$0")/.." && pwd)
exec "$prefix/lib/dotnet/dotnet.exe" \
  "$(cygpath -m "$prefix/lib/event-manifest-compiler/event-manifest-compiler.dll")" "$@"
