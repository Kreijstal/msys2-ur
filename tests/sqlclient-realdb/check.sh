#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [PRIVATE_CONNECTION_JSON]}"
out=$(cd "$1" && pwd)
export PATH="$MINGW_PREFIX/bin:/usr/bin:$PATH"
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/RealDatabase.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NoWarn>$(NoWarn);CS0618</NoWarn><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]" /></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "$MINGW_PREFIX" <<'PY'
from pathlib import Path
import hashlib,json,sys,zipfile
out=Path(sys.argv[1]);archive=Path(sys.argv[2])/'lib/dotnet/library-packs/system.data.sqlclient.4.9.1.nupkg'
assert (out/'cache/system.data.sqlclient/4.9.1/system.data.sqlclient.4.9.1.nupkg').read_bytes()==archive.read_bytes()
with zipfile.ZipFile(archive) as z:
 path='runtimes/win/lib/net8.0/System.Data.SqlClient.dll';assert (out/'bin/Release/net8.0-windows'/path).read_bytes()==z.read(path)
(out/'source-identity.json').write_text(json.dumps({'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'implementation_sha256':hashlib.sha256((out/'bin/Release/net8.0-windows'/path).read_bytes()).hexdigest(),'exact_source_archive_and_runtime_bytes':True},indent=2)+'\n')
print('PASS exact installed source archive and selected Windows implementation bytes')
PY
timeout -k 10 30 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0-windows/Check.dll")" --self-check "$(cygpath -am "$out/preparation-results.json")"
if [[ ${SQLCLIENT_REALDB_BUILD_ONLY:-0} != 1 ]];then
 timeout -k 10 180 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0-windows/Check.dll")" "$(cygpath -am "${2:?authorized private settings required}")" "$(cygpath -am "$out/results.json")"
fi
