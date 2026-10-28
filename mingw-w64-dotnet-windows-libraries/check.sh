#!/usr/bin/env bash
# Run in CLANG64. The default source is the installed package feed.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check.sh NEW_OUTPUT_DIRECTORY [FEED]}
feed=${2:-/clang64/lib/dotnet/library-packs}
mkdir "$out"
out=$(cd "$out" && pwd)
feed=$(cd "$feed" && pwd)
cp "$here/check.cs" "$out/Program.cs"
/usr/bin/python3 - "$here/libraries.json" "$out/check.csproj" <<'PY'
import json,sys,xml.etree.ElementTree as E
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in {'TargetFramework':'net8.0','OutputType':'Exe','UseAppHost':'false','EnableNETAnalyzers':'false','NuGetAudit':'false'}.items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
for lib in json.load(open(sys.argv[1])):E.SubElement(items,'PackageReference',Include=lib['id'],Version='['+lib['version']+']')
E.indent(p);E.ElementTree(p).write(sys.argv[2],encoding='utf-8',xml_declaration=True)
PY
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear /><add key="source-built" value="$(cygpath -m "$feed")" /></packageSources></configuration>
CONFIG
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 90 /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check.dll")"
