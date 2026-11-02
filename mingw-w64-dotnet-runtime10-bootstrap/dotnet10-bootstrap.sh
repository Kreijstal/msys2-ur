#!/usr/bin/env bash
set -euo pipefail
prefix=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
runtime="$prefix/lib/dotnet10"
export DOTNET_ROOT=$(cygpath -am "$runtime") DOTNET_ROOT_X64=$(cygpath -am "$runtime")
export DOTNET_MULTILEVEL_LOOKUP=0 DOTNET_CLI_TELEMETRY_OPTOUT=1
export PATH="$prefix/bin:$PATH"
exec "$runtime/dotnet.exe" "$@"
