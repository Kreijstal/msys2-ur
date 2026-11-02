#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd)
out=$(cd "${2:?missing prepared}" && pwd)
bash "$here/build-libraries.sh" "$out"
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
mkdir "$out/extractor"
cp "$here/ExtractFixtures.cs" "$out/extractor/Program.cs"
cat > "$out/extractor/Tool.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/extractor/Tool.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/extractor/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$source/StyleCop.Analyzers")" > "$out/fixtures.json"
/usr/bin/python3 - "$here/UpstreamFixtures.json" "$out/fixtures.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))==json.load(open(sys.argv[2])), 'Extracted upstream corpus differs from pinned baseline'
PY
/usr/bin/python3 "$here/pack.py" "$source" "$out" "$here"
for kind in implementation meta;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/packages/$kind/Package.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
done
