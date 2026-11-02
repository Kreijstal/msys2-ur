#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: build.sh PREPARED_ROOT}" && pwd)
mkdir -p "$build/../feed"
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
while read -r name; do
  /clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/$name/contract/Contract.csproj")" -c Release \
    --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
  /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -m "$build/$name/Library.csproj")" -c Release \
    --configfile "$(cygpath -m "$build/NuGet.config")" -o "$(cygpath -m "$build/../feed")" -p:UseSharedCompilation=false -v:minimal
done < <(/usr/bin/python3 -c 'import json,sys;[print(x["id"]) for x in json.load(open(sys.argv[1]))]' "$here/libraries.json")
