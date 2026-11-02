#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: facades.sh WCF_BUILD IMPLEMENTATION_ASSETS}" && pwd)
implementation=$(cd "${2:?usage: facades.sh WCF_BUILD IMPLEMENTATION_ASSETS}" && pwd)
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
mkdir -p "$build/contract-assets" "$build/facade-generator"
for folder in "$build"/contracts/System.ServiceModel.*; do
  cp "$folder/bin/Release/net8.0/$(basename "$folder").dll" "$build/contract-assets/"
done
cp "$here/GenerateFacades.cs" "$build/facade-generator/"
cat > "$build/facade-generator/generator.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><Nullable>enable</Nullable></PropertyGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/facade-generator/generator.csproj")" -c Release \
  --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$build/facade-generator/bin/Release/net8.0/generator.dll")" \
  "$(cygpath -m "$build/contract-assets")" "$(cygpath -m "$implementation")" "$(cygpath -m "$build/facades")"
/usr/bin/python3 "$here/prepare-facades.py" "$build"
for name in Primitives Duplex Security Http NetTcp; do
  /clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/facades/System.ServiceModel.$name/build.csproj")" -c Release \
    --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
