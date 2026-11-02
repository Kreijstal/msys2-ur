#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: build.sh PREPARED_ROOT OUTPUT}" && pwd)
out=$(cd "${2:?usage: build.sh PREPARED_ROOT OUTPUT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "${ROSLYN414_NS20_CACHE:-$out/cache}")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 "$(dirname "$0")/check-generated.py" "$root/roslyn414-1/roslyn-source" "$root/roslyn414-1/generated" > "$out/generated-audit.log"
/usr/bin/python3 - "$root" "$out" <<'PY'
from pathlib import Path
import subprocess,sys,xml.etree.ElementTree as E
root,out=map(Path,sys.argv[1:]);source=root/'roslyn414-1/roslyn-source'
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:
 p=out/name/'Build.csproj';tree=E.parse(p);changed=False
 for file in ['License.txt','THIRD-PARTY-NOTICES.txt']:
  path=source/file;assert path.is_file()
  native=subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
  if not any(e.get('Include')==native for e in tree.iter('None')):
   E.SubElement(E.SubElement(tree.getroot(),'ItemGroup'),'None',Include=native,Pack='true',PackagePath='');changed=True
 if changed:E.indent(tree);tree.write(p,encoding='utf-8',xml_declaration=True)
PY
for name in Microsoft.CodeAnalysis Microsoft.CodeAnalysis.CSharp; do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$out/$name/Build.csproj")" -c Release \
  --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/feed")" -p:UseSharedCompilation=false -v:minimal > "$out/$name/build.log" 2>&1
 printf 'PASS original Roslyn4.14 netstandard2.0 package: %s\n' "$name"
done
