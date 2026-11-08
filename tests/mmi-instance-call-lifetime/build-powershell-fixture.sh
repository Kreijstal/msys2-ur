#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
recipe=$here/../../mingw-w64-dotnet-mmi3
mkdir "${1:?usage: build-powershell-fixture.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
/usr/bin/python3 - "$recipe/InstanceCallLifetime.cs" "$recipe/MicrosoftShared.pubkey.hex" "$out" <<'PYCODE'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
replacements={
    'internal static class InstanceCallLifetime':'public static class PowerShellInstanceCallLifetime',
    'static int Main(string[] args)':'public static int Run(string[] args)',
    '    static Source source;':'    static Source source; public static string DriverPath { get; set; }',
    'NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"instance-call-driver.dll"))':'NativeLibrary.Load(DriverPath)',

}
for old,new in replacements.items():
    assert source.count(old)==1,old
    source=source.replace(old,new)
out=Path(sys.argv[3]);(out/'Checks.cs').write_text(source)
(out/'Friend.public.snk').write_bytes(bytes.fromhex(Path(sys.argv[2]).read_text()))
PYCODE
"$MINGW_PREFIX/bin/clang" -std=c11 -shared -Wall -Wextra -Werror "$recipe/check-instance-call-lifetime.c" -o "$out/instance-call-driver.dll"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0-windows</TargetFramework><AssemblyName>Microsoft.Management.Infrastructure.Tests</AssemblyName><SignAssembly>true</SignAssembly><PublicSign>true</PublicSign><AssemblyOriginatorKeyFile>Friend.public.snk</AssemblyOriginatorKeyFile><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NoWarn>CS0618</NoWarn><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Checks.cs"/><PackageReference Include="Microsoft.Management.Infrastructure" Version="[3.0.0]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="installed" value="$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")"/></packageSources></configuration>
XML
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
