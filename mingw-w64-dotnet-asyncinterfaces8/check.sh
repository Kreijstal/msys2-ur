#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED]}"
out=$(cd "$1" && pwd)
feed=$(cygpath -am "${2:-${MINGW_PREFIX}/lib/dotnet/library-packs}")
cp "$here/check.cs" "$out/Program.cs"
cat > "$out/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Bcl.AsyncInterfaces" Version="[8.0.0]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built" value="$feed"/></packageSources></configuration>
CONFIG
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 30 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check.dll")"
