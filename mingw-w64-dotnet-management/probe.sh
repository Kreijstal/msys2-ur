#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: probe.sh PREPARED_ROOT NATIVE_DIRECTORY NEW_OUTPUT}" && pwd)
native=$(cd "${2:?missing native directory}" && pwd)
mkdir "${3:?missing new output}"
out=$(cd "$3" && pwd)
cp "$here/Probe.cs" "$here/PortChecks.cs" "$here/NativeDependencies.cs" "$here/CheckAssets.cs" "$out/"
cat > "$out/probe.csproj" <<PROJECT
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Reference Include="System.Management"><HintPath>$(cygpath -m "$build/System.Management/bin/Release/net8.0-windows/System.Management.dll")</HintPath></Reference><PackageReference Include="System.CodeDom" Version="[8.0.0]"/></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/probe.csproj")" -c Release --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
cp "$native/msys-wmi-native.dll" "$out/bin/Release/net8.0/"
timeout 90 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/probe.dll")"
