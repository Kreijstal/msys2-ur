#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
consumer=$(cd "${1:?usage: check-api.sh CONSUMER NEW_OUTPUT}" && pwd)
mkdir "${2:?}";out=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for tool in Api Inventory Metadata;do
 mkdir "$out/$tool";cp "$here/Inspect$tool.cs" "$out/$tool/Program.cs"
 cat > "$out/$tool/Tool.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
XML
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Tool.csproj")" -c Release --configfile "$(cygpath -am "$consumer/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
for name in Microsoft.CodeAnalysis.NetAnalyzers Microsoft.CodeAnalysis.CSharp.NetAnalyzers Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers;do
 target=$(cygpath -am "$consumer/bin/Release/net8.0/$name.dll")
 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Api/bin/Release/net8.0/Tool.dll")" "$(cygpath -am /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$target" > "$out/$name.dll-api.json"
 for tool in Inventory Metadata;do
  /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/$tool/bin/Release/net8.0/Tool.dll")" "$target" > "$out/$name.dll-$(echo "$tool" | tr '[:upper:]' '[:lower:]').json"
 done
done
python3 - "$here/ExpectedAssemblies.json" "$out" <<'PY'
from pathlib import Path
import json,sys
expected=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2])
for name,wanted in expected.items():
 for key in ['api','inventory','metadata']:
  actual=json.loads((out/(name+'-'+key+'.json')).read_text())
  if key!='metadata':assert actual==wanted[key],(name,key)
  else:
   for field in ['name','version','culture','public_key_token','resources']:assert actual[field]==wanted[key][field],(name,field)
   assert actual['versions']['AssemblyFileVersionAttribute']==wanted[key]['versions']['AssemblyFileVersionAttribute']
   assert actual['versions']['AssemblyInformationalVersionAttribute']=='8.0.0-preview.26274.2+0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4'
print('PASS all3 original identities,3471 public/protected API declarations,293 analyzer/189 fixer/232 ID constant entries and neutral resource metadata')
PY
