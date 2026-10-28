#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED] [COMMON_API] [CSHARP_API] [COMMON_LOCALIZATION] [CSHARP_LOCALIZATION]}"
output=$(cd "$1" && pwd)
feed=${2:-/clang64/lib/dotnet/library-packs}
common_api=${3:-/clang64/share/doc/dotnet-codeanalysis-common/PublicAPI.txt}
csharp_api=${4:-/clang64/share/doc/dotnet-codeanalysis-csharp/PublicAPI.txt}
common_localization=${5:-/clang64/share/doc/dotnet-codeanalysis-common/localization.json}
csharp_localization=${6:-/clang64/share/doc/dotnet-codeanalysis-csharp/localization.json}
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home")
export NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
cp "$here/Check.cs" "$here/CheckApi.cs" "$output/"
cp "$common_api" "$output/api-common.txt"
cp "$csharp_api" "$output/api-csharp.txt"
cp "$common_localization" "$output/localization-common.json"
cp "$csharp_localization" "$output/localization-csharp.json"
cat > "$output/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><Nullable>enable</Nullable><LangVersion>12.0</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]" /></ItemGroup></Project>
PROJECT
cat > "$output/NuGet.config" <<CONFIG
<configuration><packageSources><clear /><add key="source-built" value="$(cygpath -m "$feed")" /></packageSources></configuration>
CONFIG
cd "$output"
/clang64/lib/dotnet/dotnet.exe build check.csproj -c Release --configfile NuGet.config \
  -p:UseSharedCompilation=false -v:minimal
timeout 90 /clang64/lib/dotnet/dotnet.exe bin/Release/net8.0/check.dll \
  "$(cygpath -m /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" \
  "$(cygpath -m "$output/api-common.txt")" "$(cygpath -m "$output/api-csharp.txt")" \
  "$(cygpath -m "$output/localization-common.json")" "$(cygpath -m "$output/localization-csharp.json")"
