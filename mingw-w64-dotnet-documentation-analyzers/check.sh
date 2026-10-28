#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED] [DATA_DIRECTORY]}";out=$(cd "$1" && pwd)
data=$(cd "${3:-/clang64/share/doc/dotnet-documentation-analyzers}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
compiler=$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-4.9.2)
cp "$here/Check.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><WarningsAsErrors>CS9057;CS8032;AD0001</WarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="DotNetAnalyzers.DocumentationAnalyzers" Version="[1.0.0-beta.59]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/><PackageReference Include="CommonMark.NET" Version="[0.15.1]"/><None Include="payload/DocumentationAnalyzers*.dll" Link="%(Filename)%(Extension)" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -m /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ -n ${2:-} ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources></configuration>\n' >> "$out/NuGet.config"
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Check.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
mkdir "$out/payload"
cp "$out/empty-packages/dotnetanalyzers.documentationanalyzers.unstable/1.0.0.59/analyzers/dotnet/cs/"DocumentationAnalyzers*.dll "$out/payload/"
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --no-restore -p:UseSharedCompilation=false "-p:CscToolPath=$compiler" -p:CscToolExe=csc49.cmd -v:minimal
timeout 240 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$data/ExpectedInventory.json")" "$(cygpath -am "$data/localization.json")" "$(cygpath -am "$data/fixtures.json")" "$(cygpath -am /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$out/fixture-results.json")"
mkdir "$out/inventory"
cp "$here/InspectInventory.cs" "$out/inventory/Program.cs"
cat > "$out/inventory/Tool.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/inventory/Tool.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
for name in DocumentationAnalyzers DocumentationAnalyzers.CodeFixes;do
 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/inventory/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$out/bin/Release/net8.0/$name.dll")" > "$out/inventory/$name.json"
done
/usr/bin/python3 - "$data/ExpectedInventory.json" "$out/inventory" "$out/fixture-results.json" <<'PY'
from pathlib import Path
import json,sys
for name,expected in json.load(open(sys.argv[1])).items():
 actual=json.loads((Path(sys.argv[2])/(name+'.json')).read_text());assert actual==expected,(name,actual,expected)
report=json.load(open(sys.argv[3]));assert len(report['passed'])==296 and not report['failures'] and len(report['analyzers'])==18 and len(report['code_fixes'])==14
print('PASS exact metadata-only published analyzer/fixer/ID/resource inventories and all 296 vectors/all provider coverage')
PY
# Real NuGet analyzer asset loading through only the requested meta-package.
mkdir "$out/sample"
cat > "$out/sample/Sample.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><GenerateDocumentationFile>true</GenerateDocumentationFile><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><WarningsAsErrors>CS9057;CS8032;AD0001</WarningsAsErrors><NoWarn>CS1591</NoWarn></PropertyGroup><ItemGroup><PackageReference Include="DotNetAnalyzers.DocumentationAnalyzers" Version="[1.0.0-beta.59]"/></ItemGroup></Project>
PROJECT
printf 'root = true\n[*.cs]\ndotnet_diagnostic.DOC103.severity = error\n' > "$out/sample/.editorconfig"
cat > "$out/sample/Sample.cs" <<'CS'
/// <summary>Don&apos;t encode the apostrophe.</summary>
class Owned {}
CS
args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false "-p:CscToolPath=$compiler" -p:CscToolExe=csc49.cmd -v:minimal)
set +e
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/sample/Sample.csproj")" "${args[@]}" > "$out/sample-negative.log" 2>&1
status=$?
set -e
[[ $status != 0 ]] && grep -q 'error DOC103' "$out/sample-negative.log"
cat > "$out/sample/Sample.cs" <<'CS'
/// <summary>Don't encode the apostrophe.</summary>
class Owned {}
CS
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/sample/Sample.csproj")" "${args[@]}"
printf '%s\n' 'PASS exact meta/implementation asset selection in actual MSBuild: expected DOC103 failure then corrected success through installed source compiler49'
