#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
doc=$MINGW_PREFIX/share/doc/dotnet-windows-compatibility
pwsh=${COMPAT_PWSH:-$MINGW_PREFIX/bin/pwsh.exe}
mkdir "${1:?usage: check.sh NEW_OUTPUT}"
out=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am "$MINGW_PREFIX/lib/dotnet") DOTNET_ROOT_X64=$(cygpath -am "$MINGW_PREFIX/lib/dotnet")
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/Integration.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.Windows.Compatibility" Version="[8.0.31]"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]"/></ItemGroup></Project>
XML
printf '<configuration><packageSources><clear/><add key="installed-source" value="%s"/></packageSources></configuration>\n' "$(cygpath -am "$MINGW_PREFIX/lib/dotnet/library-packs")" > "$out/NuGet.config"
"$MINGW_PREFIX/lib/dotnet/dotnet.exe" build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout -k 10 120 "$MINGW_PREFIX/lib/dotnet/dotnet.exe" "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$out/standalone")" "$(cygpath -am "$doc/dependency-groups.json")" "$(cygpath -am "$out/standalone.json")"
/usr/bin/python3 "$repo/mingw-w64-dotnet-windows-compatibility/verify-consumer.py" "$doc" "$out" "$MINGW_PREFIX/lib/dotnet/library-packs"
for mode in STA MTA; do
  timeout -k 10 120 "$pwsh" -NoLogo -NoProfile -NonInteractive "-$mode" -ExecutionPolicy Bypass \
    -File "$(cygpath -am "$here/Run.ps1")" -Fixture "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" \
    -Root "$(cygpath -am "$out/powershell-$mode")" -Graph "$(cygpath -am "$doc/dependency-groups.json")" -Result "$(cygpath -am "$out/powershell-$mode.json")"
done
/usr/bin/python3 "$here/verify.py" "$out"
