#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd)
out=$(cd "${2:?missing prepared}" && pwd)
bash "$here/build-libraries.sh" "$out"
bash "$here/generate-config.sh" "$out" "$source"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/fixture-tool/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$source/src/Microsoft.CodeAnalysis.Analyzers/UnitTests")" > "$out/fixtures.json"
/usr/bin/python3 - "$here/UpstreamFixtures.json" "$out/fixtures.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))==json.load(open(sys.argv[2])), 'Regenerated original/owned fixture data changed'
PY
/usr/bin/python3 "$here/pack.py" "$source" "$out" "$here"
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/package/Package.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
