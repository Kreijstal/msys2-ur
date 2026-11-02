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
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.NETCore.Platforms" Version="[1.1.0]" GeneratePathProperty="true"/><Content Include="$(PkgMicrosoft_NETCore_Platforms)/runtime.json" Link="source-runtime.json" CopyToOutputDirectory="PreserveNewest"/><Reference Include="NuGet.Packaging"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.dll</HintPath></Reference><Reference Include="NuGet.Common"><HintPath>$(MSBuildToolsPath)/NuGet.Common.dll</HintPath></Reference><Reference Include="NuGet.Versioning"><HintPath>$(MSBuildToolsPath)/NuGet.Versioning.dll</HintPath></Reference><Reference Include="NuGet.Frameworks"><HintPath>$(MSBuildToolsPath)/NuGet.Frameworks.dll</HintPath></Reference><Reference Include="NuGet.Packaging.Core"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.Core.dll</HintPath></Reference><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildToolsPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Check.dll")"

mkdir "$out/strict-standard"
cat > "$out/strict-standard/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/strict-standard/Check.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
/usr/bin/python3 - "$out" <<'PYCHECK'
from pathlib import Path
import json,sys
out=Path(sys.argv[1]);assets=json.loads((out/'strict-standard/obj/project.assets.json').read_text())
assert not assets.get('logs'),assets.get('logs')
assert 'NETStandard.Library/2.0.3' in assets['libraries'] and 'Microsoft.NETCore.Platforms/1.1.0' in assets['libraries']
cached=out/'empty-packages/microsoft.netcore.platforms/1.1.0/microsoft.netcore.platforms.1.1.0.nupkg'
assert cached.read_bytes()==(out/'source-feed/microsoft.netcore.platforms.1.1.0.nupkg').read_bytes()
(out/'strict-standard-results.json').write_text(json.dumps(dict(NETStandard_Library='2.0.3',Platforms='1.1.0',TreatWarningsAsErrors=True,diagnostics=assets.get('logs',[]),cached_source_archive_bytes_verified=True),indent=2)+'\n')
print('PASS strict original NETStandard.Library2.0.3 restore selects source Platforms1.1.0 with zero diagnostics')
PYCHECK
