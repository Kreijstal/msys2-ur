#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/PersistenceChecks.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><PackageReference Include="System.Management" Version="[8.0.0]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "$MINGW_PREFIX/lib/dotnet/library-packs" <<'PY'
from pathlib import Path
import sys, zipfile, hashlib
out, feed = map(Path, sys.argv[1:])
archive = next(p for p in feed.glob('*.nupkg') if p.name.lower() == 'system.management.8.0.0.nupkg')
assert (out/'cache/system.management/8.0.0/system.management.8.0.0.nupkg').read_bytes() == archive.read_bytes()
with zipfile.ZipFile(archive) as z:
    for path in ['runtimes/win/lib/net8.0/System.Management.dll','runtimes/win-x64/native/msys-wmi-native.dll']:
        assert (out/'bin/Release/net8.0'/path).read_bytes() == z.read(path)
print('PASS exact installed System.Management archive and managed/native asset bytes: '+hashlib.sha256(archive.read_bytes()).hexdigest())
PY
timeout -k 10 210 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")"
