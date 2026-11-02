#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?missing archive root}" && pwd)
out=$(cd "${2:?missing prepared output}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 "$here/validate.py" "$root" "$out" ${3:+"$3"}
/usr/bin/python3 "$here/audit-pristine.py" "$out" "$root/r" "$root/runtime-msbuild9-fa7cdded.tar.gz"
