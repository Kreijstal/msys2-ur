#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: probe.sh WCF_BUILD NEW_OUTPUT}" && pwd)
mkdir "${2:?usage: probe.sh WCF_BUILD NEW_OUTPUT}"
output=$(cd "$2" && pwd)
export PATH=${MINGW_PREFIX}/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home") NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
cp "$here/Probe.cs" "$here/CheckAssets.cs" "$here/TransportProbe.cs" "$here/SecurityProbe.cs" "$output/"
cat > "$output/probe.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><Nullable>enable</Nullable></PropertyGroup><ItemGroup>
<Reference Include="System.Private.ServiceModel"><HintPath>$(cygpath -m "$build/System.Private.ServiceModel/bin/Release/net8.0/System.Private.ServiceModel.dll")</HintPath></Reference>
<Reference Include="System.Web.Services.Description"><HintPath>$(cygpath -m "$build/System.Web.Services.Description/bin/Release/net8.0/System.Web.Services.Description.dll")</HintPath></Reference>
<PackageReference Include="Microsoft.Extensions.ObjectPool" Version="[8.0.31]"/><PackageReference Include="System.Security.Cryptography.Xml" Version="[8.0.4]"/>
</ItemGroup></Project>
PROJECT
cp "$build/NuGet.config" "$output/"
cd "$output"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build probe.csproj -c Release --configfile NuGet.config -p:UseSharedCompilation=false -v:minimal
timeout 45 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe bin/Release/net8.0/probe.dll
