#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
resources=$(cygpath -am "${2:?usage: check.sh NEW_OUTPUT RESOURCE_MANIFEST [FEED]}")
mkdir "${1:?missing output}";out=$(cd "$1" && pwd)
feed=$(cygpath -am "${3:-${MINGW_PREFIX}/lib/dotnet/library-packs}")
mkdir "$out/fixture" "$out/runner"
cp "$here/Fixture.cs" "$out/fixture/"
cp "$here/Runner.cs" "$out/runner/"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built" value="$feed"/></packageSources></configuration>
CONFIG
cat > "$out/fixture/Fixture.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Security.AccessControl" Version="[6.0.1]" Aliases="sourceacl" GeneratePathProperty="true" ExcludeAssets="compile;runtime"/><Reference Include="SourceAcl6"><HintPath>$(PkgSystem_Security_AccessControl)/ref/net8.0/System.Security.AccessControl.dll</HintPath><Aliases>sourceacl</Aliases><Private>false</Private></Reference><Content Include="$(PkgSystem_Security_AccessControl)/runtimes/win/lib/net8.0/System.Security.AccessControl.dll" Link="source-implementation/System.Security.AccessControl.dll" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
cat > "$out/runner/Runner.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
for project in fixture/Fixture runner/Runner;do
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/$project.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/runner/bin/Release/net8.0/Runner.dll")" \
 "$(cygpath -m "$out/fixture/bin/Release/net8.0/source-implementation/System.Security.AccessControl.dll")" \
 "$(cygpath -m "$out/fixture/bin/Release/net8.0/Fixture.dll")" "$resources"
