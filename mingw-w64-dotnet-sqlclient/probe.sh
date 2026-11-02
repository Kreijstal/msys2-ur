#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: probe.sh PREPARED_ROOT NEW_OUTPUT}" && pwd)
mkdir "${2:?missing new output}"
out=$(cd "$2" && pwd)
cp "$here/Probe.cs" "$out/"
cat > "$out/probe.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Reference Include="System.Data.SqlClient"><HintPath>$(cygpath -m "$build/implementation/bin/Release/net8.0-windows/System.Data.SqlClient.dll")</HintPath></Reference></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/probe.csproj")" -c Release --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 30 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/probe.dll")" "${@:3}"
