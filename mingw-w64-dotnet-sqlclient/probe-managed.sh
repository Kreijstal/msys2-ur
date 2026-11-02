#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: probe-managed.sh PREPARED_ROOT NEW_OUTPUT}" && pwd)
mkdir "${2:?missing new output}"
out=$(cd "$2" && pwd)
cp "$here/ManagedTdsProbe.cs" "$out/"
cat > "$out/probe.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Reference Include="System.Data.SqlClient"><HintPath>$(cygpath -m "$build/implementation/bin/Debug/net8.0-windows/System.Data.SqlClient.dll")</HintPath></Reference></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
# Debug is the upstream configuration that exposes the Windows managed-SNI
# test switch. This does not change or package the release implementation.
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/implementation/build.csproj")" -c Debug \
  --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/probe.csproj")" -c Release \
  --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
timeout 45 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/probe.dll")"
