#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd);out=$(cd "${2:?}" && pwd)
bash "$here/build-libraries.sh" "$out"
bash "$here/generate-config.sh" "$out" "$source"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
mkdir "$out/extract";cp "$here/ExtractFixtures.cs" "$out/extract/Program.cs"
cat > "$out/extract/Tool.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
XML
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/extract/Tool.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/extract/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$source/src/NetAnalyzers/UnitTests")" "$(cygpath -am "$here/ExpectedAssemblies.json")" > "$out/fixtures.json"
python3 - "$here/UpstreamFixtures.json" "$out/fixtures.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))==json.load(open(sys.argv[2])),'Selected original/owned fixture inventory changed'
PY
python3 "$here/pack.py" "$source" "$out" "$here"
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/package/Package.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
