#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source_root=${1:?usage: check-api.sh SOURCE_ROOT PREPARED_ROOT NEW_OUTPUT_ROOT}
prepared=${2:?missing prepared root}
out=${3:?missing output root}
mkdir "$out"
out=$(cd "$out" && pwd)
source_root=$(cd "$source_root" && pwd)
prepared=$(cd "$prepared" && pwd)
cp "$here/check-api.cs" "$out/Program.cs"
/usr/bin/python3 - "$here/libraries.json" "$source_root" "$out" <<'PY'
import json,sys,xml.etree.ElementTree as E
from pathlib import Path
manifest,source,out=map(Path,sys.argv[1:])
def project(path,props,compile=None):
    p=E.Element('Project',Sdk='Microsoft.NET.Sdk');g=E.SubElement(p,'PropertyGroup')
    for k,v in dict(TargetFramework='net8.0-windows',Nullable='annotations',EnableNETAnalyzers='false',NuGetAudit='false',**props).items():E.SubElement(g,k).text=v
    if compile:
        # Main project and source roots are siblings under makepkg's srcdir.
        import os
        items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=os.path.relpath(compile,path.parent).replace('\\','/'))
    E.indent(p);E.ElementTree(p).write(path,encoding='utf-8',xml_declaration=True)
project(out/'check-api.csproj',dict(OutputType='Exe',UseAppHost='false',EnableDefaultCompileItems='false'),out/'Program.cs')
for lib in json.loads(manifest.read_text()):
    folder=out/lib['id'];folder.mkdir()
    project(folder/'Contract.csproj',dict(AssemblyName=lib['id'],EnableDefaultCompileItems='false',NoWarn='CS0108;CS0067;CS0809;CS3021;SYSLIB0003;SYSLIB0051'),source/'src/libraries'/lib['id']/'ref'/(lib['id']+'.cs'))
PY
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
config="$prepared/NuGet.config"
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check-api.csproj")" -c Release --configfile "$(cygpath -m "$config")" -p:UseSharedCompilation=false -v:minimal
while IFS=$'\t' read -r id framework; do
  /clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/$id/Contract.csproj")" -c Release --configfile "$(cygpath -m "$config")" -p:UseSharedCompilation=false -v:minimal
  /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0-windows/check-api.dll")" \
    "$(cygpath -m "$out/$id/bin/Release/net8.0-windows/$id.dll")" \
    "$(cygpath -m "$prepared/$id/bin/Release/$framework/$id.dll")"
done < <(/usr/bin/python3 -c 'import json,sys; [print(v["id"]+"\t"+v["framework"]) for v in json.load(open(sys.argv[1]))]' "$here/libraries.json")
