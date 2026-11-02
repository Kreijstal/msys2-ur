#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
feed=$(cygpath -am "${2:-/clang64/lib/dotnet/library-packs}")
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED]}";out=$(cd "$1" && pwd)
cp "$here/Check.cs" "$out/Program.cs"
/usr/bin/python3 - "$out" "${2:-/clang64/lib/dotnet/library-packs}" <<'PYVIEW'
from pathlib import Path
import os,shutil,sys
out,candidate=(Path(p) for p in sys.argv[1:]);view=out/'source-feed';view.mkdir();selected={}
for base in [candidate,Path('/clang64/lib/dotnet/library-packs')]:
 for p in base.glob('*.nupkg'):selected.setdefault(p.name.lower(),p)
for n,p in selected.items():
 try:os.link(p,view/n)
 except OSError:shutil.copyfile(p,view/n)
PYVIEW
feed=$(cygpath -am "$out/source-feed")
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built" value="$feed"/></packageSources></configuration>
CONFIG
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.NETCore.Platforms" Version="[2.1.2]" GeneratePathProperty="true"/><Content Include="$(PkgMicrosoft_NETCore_Platforms)/runtime.json" Link="source-runtime.json" CopyToOutputDirectory="PreserveNewest"/><Reference Include="NuGet.Packaging"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.dll</HintPath></Reference><Reference Include="NuGet.Common"><HintPath>$(MSBuildToolsPath)/NuGet.Common.dll</HintPath></Reference><Reference Include="NuGet.Versioning"><HintPath>$(MSBuildToolsPath)/NuGet.Versioning.dll</HintPath></Reference><Reference Include="NuGet.Frameworks"><HintPath>$(MSBuildToolsPath)/NuGet.Frameworks.dll</HintPath></Reference><Reference Include="NuGet.Packaging.Core"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.Core.dll</HintPath></Reference><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildToolsPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Check.dll")"


/usr/bin/python3 - "$out" "${2:-/clang64/lib/dotnet/library-packs}" <<'PYVERIFY'
from pathlib import Path
import json,sys
out,feed=map(Path,sys.argv[1:]);assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets.get('logs')
assert set(assets['libraries'])=={'Microsoft.NETCore.Platforms/2.1.2'}
archive=out/'empty-packages/microsoft.netcore.platforms/2.1.2/microsoft.netcore.platforms.2.1.2.nupkg';candidate=next(p for p in feed.glob('*.nupkg') if p.name.lower()=='microsoft.netcore.platforms.2.1.2.nupkg');assert archive.read_bytes()==candidate.read_bytes()
print('PASS exact source Platforms2.1.2 archive and zero-diagnostic fresh installed-feed restore')
PYVERIFY
