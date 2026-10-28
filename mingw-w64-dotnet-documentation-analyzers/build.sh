#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd);out=$(cd "${2:?missing prepared}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for project in DocumentationAnalyzers.CodeFixes fixture-tool inventory-tool;do
 filename=Library.csproj;[[ $project == DocumentationAnalyzers.CodeFixes ]]||filename=Tool.csproj
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$project/$filename")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/fixture-tool/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$source/DocumentationAnalyzers/DocumentationAnalyzers.Test")" > "$out/fixtures.json"
/usr/bin/python3 - "$here/UpstreamFixtures.json" "$out/fixtures.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))==json.load(open(sys.argv[2])), 'Regenerated source fixture corpus differs'
PY
/usr/bin/python3 "$here/pack.py" "$source" "$out" "$here"
for kind in implementation meta;do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/packages/$kind/Package.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
done
