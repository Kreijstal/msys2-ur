#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED] [DATA_DIRECTORY]}";out=$(cd "$1" && pwd)
data=$(cd "${3:-${MINGW_PREFIX}/share/doc/dotnet-stylecop-analyzers}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
compiler=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
CONFIG
if [[ -n ${2:-} ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources></configuration>\n' >> "$out/NuGet.config"
build_tool() {
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$1")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false "-p:CscToolPath=$compiler" -p:CscToolExe=csc49.cmd -v:minimal
}
for tool in inventory fixtures;do mkdir "$out/$tool";done
cp "$here/CheckPrototype.cs" "$out/Program.cs"
cp "$here/CheckGenerated.cs" "$out/"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><RunAnalyzersDuringBuild>false</RunAnalyzersDuringBuild><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><Compile Include="CheckGenerated.cs"/><PackageReference Include="StyleCop.Analyzers" Version="[1.2.0-beta.556]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
build_tool "$out/Check.csproj"
assets="$out/empty-packages/stylecop.analyzers.unstable/1.2.0.556/analyzers/dotnet/cs"
cp -r "$assets/." "$out/bin/Release/net8.0/"
timeout 120 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$data/ExpectedInventory.json")" "$(cygpath -am "$data/localization.json")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$data/baseline")" "$(cygpath -am "$data/regenerated")"
cp "$here/CheckFixtures.cs" "$out/fixtures/Program.cs"
cp "$here/CheckSpecialFixes.cs" "$out/fixtures/"
cat > "$out/fixtures/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><RunAnalyzersDuringBuild>false</RunAnalyzersDuringBuild><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="StyleCop.Analyzers" Version="[1.2.0-beta.556]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
build_tool "$out/fixtures/Check.csproj"
cp -r "$assets/." "$out/fixtures/bin/Release/net8.0/"
timeout 600 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/fixtures/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$data/fixtures.json")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$out/fixture-results.json")"
cp "$here/InspectInventory.cs" "$out/inventory/Program.cs"
cat > "$out/inventory/Tool.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
build_tool "$out/inventory/Tool.csproj"
for name in StyleCop.Analyzers StyleCop.Analyzers.CodeFixes;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/inventory/bin/Release/net8.0/Tool.dll")" "$(cygpath -am "$out/bin/Release/net8.0/$name.dll")" > "$out/inventory/$name.json"
done
/usr/bin/python3 - "$data/ExpectedInventory.json" "$out/inventory" "$data/fixtures.json" "$out/fixture-results.json" <<'PY'
from pathlib import Path
import json,sys
expected=json.load(open(sys.argv[1]))
for key,name in [('analyzers','StyleCop.Analyzers'),('codefixes','StyleCop.Analyzers.CodeFixes')]:
 assert json.loads((Path(sys.argv[2])/(name+'.json')).read_text())==expected[key],name
corpus=json.load(open(sys.argv[3]));report=json.load(open(sys.argv[4]))
assert not report['failures'] and len(report['passed'])==len(corpus['fixtures'])
assert len(report['owned_passed'])==16
assert set(expected['codefixes']['code_fixes']).issubset(report['code_fixes']), 'Every exported code-fix provider must execute a passing action'
print('PASS exact independent published metadata inventories and every selected upstream fixture')
PY
# Request only the original meta-package: analyzer selection must flow through
# its implementation dependency, without a manual Analyzer Include.
mkdir "$out/sample"
cat > "$out/sample/Sample.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><WarningsAsErrors>SA1001;CS9057;CS8032;AD0001</WarningsAsErrors></PropertyGroup><ItemGroup><PackageReference Include="StyleCop.Analyzers" Version="[1.2.0-beta.556]"/></ItemGroup></Project>
PROJECT
printf 'class C { int[] x = { 1,2 }; }\n' > "$out/sample/Sample.cs"
if build_tool "$out/sample/Sample.csproj" > "$out/sample/negative.log" 2>&1;then
 echo 'FAIL: meta-package did not enforce SA1001' >&2;exit 1
fi
grep -E 'error SA1001:' "$out/sample/negative.log"
if grep -E 'AD0001|CS8032|CS9057' "$out/sample/negative.log";then exit 1;fi
printf 'class C { int[] x = { 1, 2 }; }\n' > "$out/sample/Sample.cs"
build_tool "$out/sample/Sample.csproj" > "$out/sample/corrected.log" 2>&1
echo 'PASS real MSBuild meta/implementation analyzer assets: expected SA1001 error, then corrected build'
