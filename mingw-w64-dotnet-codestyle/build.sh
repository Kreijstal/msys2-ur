#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd);out=$(cd "${2:?}" && pwd)
bash "$here/build-libraries.sh" "$out"
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
mkdir "$out/extract";cp "$here/ExtractFixtures.cs" "$out/extract/Program.cs"
cat > "$out/extract/Tool.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/><PackageReference Include="Microsoft.CodeAnalysis.VisualBasic" Version="[4.9.2]"/></ItemGroup></Project>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/extract/Tool.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/extract/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$source")" "$(cygpath -am "$here/ExpectedAssemblies.json")" > "$out/fixtures.json"
python3 - "$here/UpstreamFixtures.json" "$out/fixtures.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))==json.load(open(sys.argv[2])),'Original selected source fixture inventory changed'
PY
python3 "$here/pack.py" "$source" "$out" "$here"
for language in CSharp VisualBasic;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/packages/$language/Package.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
done
