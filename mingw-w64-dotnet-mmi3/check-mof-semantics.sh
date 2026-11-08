#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check-mof-semantics.sh NEW_OUTPUT [FEED]}"
out=$(cd "$1" && pwd)
feed=$(cygpath -am "${2:-$MINGW_PREFIX/lib/dotnet/library-packs}")
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/MofSemantics.cs" "$out/Program.cs"
key=$here/MicrosoftShared.pubkey.hex
[[ -f $key ]] || key=$here/../../mingw-w64-dotnet-mmi3/MicrosoftShared.pubkey.hex
/usr/bin/python3 - "$key" "$out/Friend.public.snk" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[2]).write_bytes(bytes.fromhex(Path(sys.argv[1]).read_text()))
PY
"$MINGW_PREFIX/bin/clang" -std=c11 -shared -Wall -Wextra -Werror "$here/native-oracle.c" -lmi -o "$out/native-oracle.dll"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>System.Management.Automation</AssemblyName><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>Friend.public.snk</AssemblyOriginatorKeyFile><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><None Include="native-oracle.dll" CopyToOutputDirectory="PreserveNewest"/><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="source-port" value="$feed"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/usr/bin/python3 - "$out" "${2:-$MINGW_PREFIX/lib/dotnet/library-packs}" <<'PY'
from pathlib import Path
import hashlib,sys,zipfile
out,feed=map(Path,sys.argv[1:])
archive=next(p for p in feed.iterdir() if p.name.lower()=='microsoft.management.infrastructure.3.0.0.nupkg')
assert (out/'cache/microsoft.management.infrastructure/3.0.0/microsoft.management.infrastructure.3.0.0.nupkg').read_bytes()==archive.read_bytes()
with zipfile.ZipFile(archive) as z:
    dll=out/'bin/Release/net8.0/Microsoft.Management.Infrastructure.dll'
    assert any(dll.read_bytes()==z.read(name) for name in z.namelist() if name.startswith('lib/') and name.endswith('/Microsoft.Management.Infrastructure.dll'))
print('PASS exact source feed archive and implementation bytes; archive SHA256 '+hashlib.sha256(archive.read_bytes()).hexdigest())
PY
timeout -k 10 180 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/System.Management.Automation.dll")"
