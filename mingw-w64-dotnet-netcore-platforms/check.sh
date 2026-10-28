#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
feed=$(cygpath -am "${2:-/clang64/lib/dotnet/library-packs}")
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED]}";out=$(cd "$1" && pwd)
cp "$here/Check.cs" "$out/Program.cs"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="source-built" value="$feed"/></packageSources></configuration>
CONFIG
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.NETCore.Platforms" Version="[1.1.2]" GeneratePathProperty="true"/><Content Include="$(PkgMicrosoft_NETCore_Platforms)/runtime.json" Link="source-runtime.json" CopyToOutputDirectory="PreserveNewest"/><Reference Include="NuGet.Packaging"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.dll</HintPath></Reference><Reference Include="NuGet.Common"><HintPath>$(MSBuildToolsPath)/NuGet.Common.dll</HintPath></Reference><Reference Include="NuGet.Versioning"><HintPath>$(MSBuildToolsPath)/NuGet.Versioning.dll</HintPath></Reference><Reference Include="NuGet.Frameworks"><HintPath>$(MSBuildToolsPath)/NuGet.Frameworks.dll</HintPath></Reference><Reference Include="NuGet.Packaging.Core"><HintPath>$(MSBuildToolsPath)/NuGet.Packaging.Core.dll</HintPath></Reference><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildToolsPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/Check.csproj")" -c Release --configfile "$(cygpath -m "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/Check.dll")"
