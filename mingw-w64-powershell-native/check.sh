#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [FEED] [EXPECTED_HEADER]}"
output=$(cd "$1" && pwd)
feed=${2:-/clang64/lib/dotnet/library-packs}
expected=${3:-/clang64/share/doc/powershell-native/expected-events.h}
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home")
export NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
cp "$here/check-native.cpp" "$output/"
cp "$expected" "$output/expected-events.h"
cat > "$output/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><RuntimeIdentifier>win-x64</RuntimeIdentifier><SelfContained>false</SelfContained><UseAppHost>false</UseAppHost><CopyLocalLockFileAssemblies>true</CopyLocalLockFileAssemblies><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.PowerShell.Native" Version="[700.0.0]" /></ItemGroup></Project>
PROJECT
cat > "$output/NuGet.config" <<CONFIG
<configuration><packageSources><clear /><add key="source-built" value="$(cygpath -m "$feed")" /></packageSources></configuration>
CONFIG
cd "$output"
/clang64/lib/dotnet/dotnet.exe build check.csproj -c Release \
  --configfile NuGet.config -p:UseSharedCompilation=false -v:minimal
clang++ -std=c++14 -O2 -municode check-native.cpp -lversion -o check-native.exe
timeout 45 ./check-native.exe \
  "$(cygpath -m "$output/bin/Release/net8.0/win-x64/pwrshplugin.dll")" \
  "$(cygpath -m "$output/bin/Release/net8.0/win-x64/PowerShell.Core.Instrumentation.dll")"
