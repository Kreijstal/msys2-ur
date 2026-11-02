#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT [NEW_FEED]}
mkdir "$out";out=$(cd "$out" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
XML
if [[ $# -ge 2 ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 2 ]];then
  printf '<packageSourceMapping><packageSource key="new-source"><package pattern="NuGet.*"/></packageSource><packageSource key="installed-source"><package pattern="*"/></packageSource></packageSourceMapping>\n' >> "$out/NuGet.config"
fi
printf '</configuration>\n' >> "$out/NuGet.config"
cp "$here/Smoke.cs" "$here/ProtocolChecks.cs" "$here/SigningChecks.cs" "$out/"
/usr/bin/python3 - "$here" "$out" <<'PY'
from pathlib import Path
import json,sys,xml.etree.ElementTree as E
here,out=(Path(p) for p in sys.argv[1:])
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(props,name).text=value
items=E.SubElement(p,'ItemGroup')
for filename in ['Smoke.cs','ProtocolChecks.cs','SigningChecks.cs']:E.SubElement(items,'Compile',Include=filename)
for name in json.loads((here/'libraries.json').read_text()):E.SubElement(items,'PackageReference',Include=name,Version='[6.9.1]')
E.indent(p);E.ElementTree(p).write(out/'Check.csproj',encoding='utf-8',xml_declaration=True)
PY
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$out/owned")"
mkdir "$out/inspect" "$out/pe" "$out/api"
cp "$here/InspectApi.cs" "$out/inspect/"
cp "$here/InspectAssemblyMetadata.cs" "$out/pe/"
cat > "$out/inspect/Inspect.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="InspectApi.cs"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
XML
cat > "$out/pe/Inspect.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="InspectAssemblyMetadata.cs"/></ItemGroup></Project>
XML
for tool in inspect pe;do
  ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$tool/Inspect.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
assemblies=()
for path in "$out/bin/Release/net8.0"/NuGet.*.dll;do
  name=$(basename "$path" .dll)
  ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/inspect/bin/Release/net8.0/Inspect.dll")" \
    "$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$path")" > "$out/api/$name.json"
  assemblies+=("$(cygpath -am "$path")")
done
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/pe/bin/Release/net8.0/Inspect.dll")" "${assemblies[@]}" > "$out/metadata.json"
/usr/bin/python3 "$here/compare.py" "$here" "$out"
/usr/bin/python3 "$here/verify-consumer.py" "$here" "$out"
echo 'PASS fresh source-only NuGet consumer, original RestoreRunner behavior and complete API/resource/payload gates'
