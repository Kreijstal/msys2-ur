#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
recipe=$here/../../mingw-w64-dotnet-mmi3
mkdir "${1:?usage: build-powershell-fixture.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$recipe/SyncResultChecks.cs" "$out/Checks.cs"
/usr/bin/python3 - "$recipe/MicrosoftShared.pubkey.hex" "$out/Friend.public.snk" <<'PYCODE'
from pathlib import Path
import sys
Path(sys.argv[2]).write_bytes(bytes.fromhex(Path(sys.argv[1]).read_text()))
PYCODE
"$MINGW_PREFIX/bin/clang" -std=c11 -shared -Wall -Wextra -Werror "$recipe/check-sync-results.c" -o "$out/sync-results-driver.dll"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><AssemblyName>Microsoft.Management.Infrastructure.Tests</AssemblyName><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>Friend.public.snk</AssemblyOriginatorKeyFile><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NoWarn>CS0618</NoWarn><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Checks.cs"/><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
