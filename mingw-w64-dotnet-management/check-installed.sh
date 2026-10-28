#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: check-installed.sh NEW_OUTPUT RESOURCE_MANIFEST [NEW_FEED]}
resources=$(cygpath -am "${2:?missing resource manifest}")
mkdir "$out"
out=$(cd "$out" && pwd)
cp "$here/Probe.cs" "$here/PortChecks.cs" "$here/ApartmentChecks.cs" "$here/NativeDependencies.cs" "$here/CheckAssets.cs" "$out/"
cat > "$out/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Management" Version="[8.0.0]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source-built" value="$(cygpath -m /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ $# -ge 3 ]]; then
  printf '<add key="new-source-built" value="%s"/>\n' "$(cygpath -am "$3")" >> "$out/NuGet.config"
fi
printf '</packageSources>\n' >> "$out/NuGet.config"
if [[ $# -ge 3 ]]; then
  cat >> "$out/NuGet.config" <<'MAPPING'
<packageSourceMapping>
 <packageSource key="new-source-built"><package pattern="System.Management"/></packageSource>
 <packageSource key="installed-source-built"><package pattern="*"/></packageSource>
</packageSourceMapping>
MAPPING
fi
printf '</configuration>\n' >> "$out/NuGet.config"
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check.csproj")" -c Release \
  --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "${3:-/clang64/lib/dotnet/library-packs}" <<'PY'
from pathlib import Path
import hashlib,sys,zipfile
out,feed=(Path(p) for p in sys.argv[1:])
expected=[p for p in feed.glob('*.nupkg') if p.name.lower()=='system.management.8.0.0.nupkg']
assert len(expected)==1
cached=out/'empty-packages/system.management/8.0.0/system.management.8.0.0.nupkg'
assert cached.read_bytes()==expected[0].read_bytes(),'Consumer restored a different System.Management source package'
with zipfile.ZipFile(expected[0]) as archive:
 for name in ['runtimes/win/lib/net8.0/System.Management.dll','runtimes/win-x64/native/msys-wmi-native.dll']:
  assert (out/'bin/Release/net8.0'/name).read_bytes()==archive.read(name),name
print('PASS consumer restored exact candidate/installed source archive and loads its exact managed/native asset bytes')
PY
timeout 90 /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check.dll")" "$resources"
