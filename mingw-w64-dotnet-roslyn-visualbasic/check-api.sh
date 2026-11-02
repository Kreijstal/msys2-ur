#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
consumer=$(cd "${1:?usage: check-api.sh CONSUMER NEW_OUTPUT}" && pwd)
mkdir "${2:?missing new output}";out=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cp "$consumer/NuGet.config" "$out/"
for tool in api metadata;do
 mkdir "$out/$tool"
 filename=InspectApi.cs;[[ $tool == api ]]||filename=InspectMetadata.cs
 cp "$here/$filename" "$out/$tool/Program.cs"
 cat > "$out/$tool/Tool.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Tool.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
target=$(cygpath -am "$consumer/bin/Release/net8.0/Microsoft.CodeAnalysis.VisualBasic.dll")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/api/bin/Release/net8.0/Tool.dll")" "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$target" > "$out/actual-api.json"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/metadata/bin/Release/net8.0/Tool.dll")" "$target" > "$out/actual-metadata.json"
/usr/bin/python3 - "$here" "$out" <<'PY'
from pathlib import Path
import json,sys
expected,actual=(Path(p) for p in sys.argv[1:])
assert json.loads((expected/'ExpectedApi.json').read_text())==json.loads((actual/'actual-api.json').read_text()), 'Published API mismatch'
e=json.loads((expected/'ExpectedMetadata.json').read_text());a=json.loads((actual/'actual-metadata.json').read_text())
for key in ['name','version','culture','public_key_token','resources']:assert a[key]==e[key],key
assert not any(r['name'].startswith('Microsoft.VisualBasic') for r in a['references']), 'Compiler must embed its own VB runtime support'
print('PASS all 6176 published API declarations, original identity, 1795 neutral strings and byte-identical four embedded source templates; no normal VB runtime assembly reference')
PY
