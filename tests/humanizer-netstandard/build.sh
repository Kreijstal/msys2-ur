#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build.sh PREPARED_OUTPUT}" && pwd)
source="$out/Humanizer-3ebc38de585fc641a04b0e78ed69468453b0f8a1"
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 - "$out" <<'PY'
from pathlib import Path
import shutil,subprocess,sys,xml.etree.ElementTree as E
out=Path(sys.argv[1]);source=out/'Humanizer-3ebc38de585fc641a04b0e78ed69468453b0f8a1'
assets=out/'assets';assets.mkdir(exist_ok=True)
path=out/'PackageAssets.targets';tree=E.parse(path)
for group in tree.findall('ItemGroup'):
 for item in list(group):
  if item.tag=='None':group.remove(item)
items=E.SubElement(tree.getroot(),'ItemGroup')
for relative,name in [('LICENSE','LICENSE'),('src/Humanizer/Bytes/LICENSE','LICENSE.Bytes'),('src/Humanizer/Inflections/LICENSE','LICENSE.Inflections')]:
 shutil.copyfile(source/relative,assets/name)
 native=subprocess.check_output(['cygpath','-am',str(assets/name)],text=True).strip()
 E.SubElement(items,'None',Include=native,Pack='true',PackagePath='')
E.indent(tree);tree.write(path,encoding='utf-8',xml_declaration=True)
PY
/clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$source/src/Humanizer/Humanizer.csproj")" \
 -c Release -o "$(cygpath -am "$out/feed")" --configfile "$(cygpath -am "$out/NuGet.config")" \
 -p:TargetFrameworks=netstandard2.0 -p:TargetFramework=netstandard2.0 \
 -p:ImportDirectoryBuildProps=false -p:ImportDirectoryBuildTargets=false \
 -p:CustomAfterMicrosoftCommonTargets="$(cygpath -am "$out/PackageAssets.targets")" \
 -p:PackageId=Humanizer.Core -p:PackageVersion=2.14.1 -p:Version=2.14.1 \
 -p:AssemblyVersion=2.14.0.0 -p:FileVersion=2.14.1.0 \
 -p:InformationalVersion=2.14.1+3ebc38de585fc641a04b0e78ed69468453b0f8a1 \
 -p:IncludeSourceRevisionInInformationalVersion=false \
 -p:RepositoryUrl=https://github.com/Humanizr/Humanizer -p:RepositoryCommit=3ebc38de585fc641a04b0e78ed69468453b0f8a1 \
 -p:EnableNETAnalyzers=false -p:NuGetAudit=false -p:UseSharedCompilation=false \
 > "$out/build.log" 2>&1
printf '%s\n' 'PASS unchanged original Humanizer netstandard2.0 project'
