#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
recipe=$here/../../mingw-w64-dotnet-sqlclient
mkdir "${1:?usage: build-powershell-fixture.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 - "$recipe/LocalDbChecks.cs" "$out/Checks.cs" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
replacements={
    'internal static class LocalDbChecks':'public static class PowerShellLocalDbChecks',
    'private static int Main(string[] args)':'public static int Run(string[] args)',
    'library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"localdb-driver.dll"));':
    'library=NativeLibrary.Load(args.Single(value=>value.StartsWith("--driver=",StringComparison.Ordinal)).Substring(9));',
}
for old,new in replacements.items():
    assert source.count(old)==1,old
    source=source.replace(old,new)
Path(sys.argv[2]).write_text(source)
PY
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><AssemblyName>PowerShellLocalDbFixture</AssemblyName><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NoWarn>CS0618</NoWarn><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Checks.cs"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
