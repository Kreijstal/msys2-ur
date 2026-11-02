#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT RESOURCE_MANIFEST [NEW_FEED]}
resources=$(cygpath -am "${2:?missing resource manifest}")
mkdir "$out"
out=$(cd "$out" && pwd)
cp "$here/check.cs" "$here/CheckResources.cs" "$here/libraries.json" "$out/"
/usr/bin/python3 - "$here/libraries.json" "$out/check.csproj" <<'PY'
import sys,json,xml.etree.ElementTree as E
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
for lib in json.load(open(sys.argv[1])):E.SubElement(items,'PackageReference',Include=lib['id'],Version='['+lib['version']+']')
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.9.2]')
E.indent(p);E.ElementTree(p).write(sys.argv[2],encoding='utf-8',xml_declaration=True)
PY
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source-built" value="$(cygpath -m ${MINGW_PREFIX}/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 3 ]]; then
  printf '<add key="new-source-built" value="%s"/>\n' "$(cygpath -am "$3")" >> "$out/NuGet.config"
fi
printf '</packageSources></configuration>\n' >> "$out/NuGet.config"
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 120 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check.dll")" "$resources" "$(cygpath -m "$here/libraries.json")"
