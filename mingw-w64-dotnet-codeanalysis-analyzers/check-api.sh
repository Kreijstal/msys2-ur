#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
consumer=$(cd "${1:?usage: check-api.sh CONSUMER NEW_OUTPUT}" && pwd)
mkdir "${2:?missing new output}";out=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
for tool in Api Inventory Metadata;do
 mkdir "$out/$tool";cp "$here/Inspect$tool.cs" "$out/$tool/Program.cs"
 cat > "$out/$tool/Tool.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Tool.csproj")" -c Release --configfile "$(cygpath -am "$consumer/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
for name in Microsoft.CodeAnalysis.Analyzers Microsoft.CodeAnalysis.CSharp.Analyzers Microsoft.CodeAnalysis.VisualBasic.Analyzers;do
 target=$(cygpath -am "$consumer/bin/Release/net8.0/$name.dll")
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/Api/bin/Release/net8.0/Tool.dll")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$target" > "$out/$name-Api.json"
 for tool in Inventory Metadata;do ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/$tool/bin/Release/net8.0/Tool.dll")" "$target" > "$out/$name-$tool.json";done
done
/usr/bin/python3 - "$here" "$out" <<'PY'
from pathlib import Path
import json,sys
expected,out=(Path(p) for p in sys.argv[1:])
for kind in ['Api','Inventory','Metadata']:
 for name,wanted in json.loads((expected/('Expected'+kind+'.json')).read_text()).items():
  actual=json.loads((out/(name+'-'+kind+'.json')).read_text())
  if kind!='Metadata':assert actual==wanted,(name,kind)
  else:
   for key in ['name','version','culture','public_key_token','resources']:assert actual[key]==wanted[key],(name,key)
   assert actual['versions']['AssemblyFileVersionAttribute']==wanted['versions']['AssemblyFileVersionAttribute']
   assert actual['versions']['AssemblyInformationalVersionAttribute']=='3.3.4+22ea6422f85b05ca0793cc3b76375487be407f5d'
print('PASS all 325 published API declarations, complete 23 analyzer/13 fixer/46 ID inventories, original identity and neutral/banned-symbol resources')
PY
