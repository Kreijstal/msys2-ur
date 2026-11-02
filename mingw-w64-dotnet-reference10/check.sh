#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: check.sh ARCHIVE_ROOT PREPARED}" && pwd)
out=$(cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 "$here/validate.py" "$root" "$out" >"$out/validate.log" 2>&1
/usr/bin/python3 "$here/audit-pristine.py" "$out" "$root/r" "$root/runtime-v10.0.5.tar.gz" >"$out/audit.log" 2>&1
