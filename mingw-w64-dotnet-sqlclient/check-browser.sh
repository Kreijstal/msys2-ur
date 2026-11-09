#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED] [--baseline]}"
out=$(cd "$1" && pwd)
feed=$(cygpath -am "${2:-$MINGW_PREFIX/lib/dotnet/library-packs}")
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/BrowserChecks.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NoWarn>CS0618</NoWarn><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="source-port" value="$feed"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "${2:-$MINGW_PREFIX/lib/dotnet/library-packs}" <<'PY'
from pathlib import Path
import hashlib,sys,zipfile
out,feed=map(Path,sys.argv[1:])
archive=next(p for p in feed.iterdir() if p.name.lower()=='system.data.sqlclient.4.9.1.nupkg')
assert (out/'cache/system.data.sqlclient/4.9.1/system.data.sqlclient.4.9.1.nupkg').read_bytes()==archive.read_bytes()
with zipfile.ZipFile(archive) as z:
    dll=out/'bin/Release/net8.0-windows/runtimes/win/lib/net8.0/System.Data.SqlClient.dll'
    assert any(dll.read_bytes()==z.read(name) for name in z.namelist() if name=='runtimes/win/lib/net8.0/System.Data.SqlClient.dll')
print('PASS exact source feed archive and implementation bytes; archive SHA256 '+hashlib.sha256(archive.read_bytes()).hexdigest())
PY
args=(); [[ ${3:-} != --baseline ]] || args+=(--baseline)
timeout -k 10 90 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0-windows/Check.dll")" "${args[@]}"
