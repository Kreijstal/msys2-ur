#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh ARCHIVE_ROOT PREPARED}" && pwd)
out=$(cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 "$here/prepare-version.py" "$root" >"$out/version.log" 2>&1
bash "$here/evaluate.sh" "$root" "$out" >"$out/evaluate.log" 2>&1
/usr/bin/python3 "$here/build.py" "$root" "$out" >"$out/compile.log" 2>&1
