#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?usage: check.sh BUILD_ROOT NEW_OUTPUT [FEED]}" && pwd)
mkdir "${2:?missing output}";out=$(cd "$2" && pwd)
feed=$(cd "${3:-$root/feed}" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
cp "$here/Check.cs" "$out/Program.cs"
cat > "$out/Check.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.Windows.Compatibility" Version="[8.0.31]"/><PackageReference Include="System.Data.SqlClient" Version="[4.9.1]"/></ItemGroup></Project>
XML
cat > "$out/NuGet.config" <<XML
<configuration><packageSources><clear/><add key="candidate-source" value="$(cygpath -am "$feed")"/><add key="installed-source" value="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/library-packs)"/></packageSources></configuration>
XML
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 120 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$root/dependency-groups.json")"
/usr/bin/python3 "$here/verify-consumer.py" "$root" "$out" "$feed"
