#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
consumer=$(cd "${1:?usage: check-api.sh CONSUMER NEW_OUTPUT}" && pwd)
mkdir "${2:?missing output}";out=$(cd "$2" && pwd)
cp "$here/InspectApi.cs" "$out/Program.cs"
cat > "$out/Inspect.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built-tools" value="$(cygpath -m /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Inspect.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
while read -r id;do
 /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Inspect.dll")" \
  "$(cygpath -m /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" \
  "$(cygpath -m "$consumer/bin/Release/net8.0/$id.dll")" > "$out/$id.json"
done < <(/usr/bin/python3 -c 'import json,sys;[print(e) for e in json.load(open(sys.argv[1]))]' "$here/ExpectedApi.json")
/usr/bin/python3 - "$here/ExpectedApi.json" "$out" <<'PY'
import json,sys
from pathlib import Path
count=0
for name,wanted in json.load(open(sys.argv[1])).items():
 actual=json.loads((Path(sys.argv[2])/(name+'.json')).read_text())
 assert actual['identity']==wanted['identity'],(name,actual['identity'],wanted['identity'])
 missing=set(wanted['api'])-set(actual['api']);extra=set(actual['api'])-set(wanted['api'])
 for label,values in [('MISSING',missing),('EXTRA',extra)]:
  for value in sorted(values):print(name,label,value)
 assert not (missing or extra),name
 count+=len(wanted['api']);print('PASS',name,len(wanted['api']),'published declarations and exact identity')
assert count==1898,count
print('PASS all 1898 published Roslyn Workspaces public/protected declarations, no omissions or extras')
PY
