#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [PRIVATE_SETTINGS_JSON]}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/AuthenticatedSession.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "$MINGW_PREFIX" <<'PY'
from pathlib import Path
import hashlib,sys,zipfile
out,prefix=map(Path,sys.argv[1:])
archive=prefix/'lib/dotnet/library-packs/microsoft.management.infrastructure.3.0.0.nupkg'
assert (out/'cache/microsoft.management.infrastructure/3.0.0/microsoft.management.infrastructure.3.0.0.nupkg').read_bytes()==archive.read_bytes()
with zipfile.ZipFile(archive) as z:
    dll=out/'bin/Release/net8.0/Microsoft.Management.Infrastructure.dll'
    assets=[name for name in z.namelist() if name.startswith('lib/') and name.endswith('/Microsoft.Management.Infrastructure.dll')]
    assert assets and any(dll.read_bytes()==z.read(name) for name in assets)
print('PASS exact installed source archive and implementation bytes; archive SHA256 '+hashlib.sha256(archive.read_bytes()).hexdigest())
PY
timeout -k 10 45 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" --self-check
if [[ ${MMI_WSMAN_BUILD_ONLY:-0} != 1 ]]; then
  settings=$(cygpath -am "${2:?private endpoint/credential JSON required}")
  timeout -k 10 180 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$settings" "$(cygpath -am "$out/results.json")"
fi
