#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED] [API]}"
output=$(cd "$1" && pwd)
feed=$(cygpath -am "${2:-/clang64/lib/dotnet/library-packs}")
api=${3:-/clang64/share/doc/dotnet-applicationinsights/PublicAPI.txt}
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) MSBuildEnableWorkloadResolver=false DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home") NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
cp "$here/Check.cs" "$here/CheckApi.cs" "$output/"
cp "$api" "$output/PublicAPI.txt"
cat > "$output/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><Nullable>annotations</Nullable></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.ApplicationInsights" Version="[2.23.0]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cat > "$output/NuGet.config" <<CONFIG
<configuration><packageSources><clear /><add key="new-library" value="$(cygpath -m "$feed")"/><add key="installed-tools" value="$(cygpath -m /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
cd "$output"
/clang64/lib/dotnet/dotnet.exe build check.csproj -c Release --configfile NuGet.config -p:UseSharedCompilation=false -v:minimal
timeout 60 /clang64/lib/dotnet/dotnet.exe bin/Release/net8.0/check.dll \
  "$(cygpath -m /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -m "$output/PublicAPI.txt")"
