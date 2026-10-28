#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: check-legacy.sh WCF_BUILD}" && pwd)
mkdir -p "$build/legacy-check"
cp "$here/CheckLegacyMetadata.cs" "$build/legacy-check/Program.cs"
cat > "$build/legacy-check/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/legacy-check/check.csproj")" -c Release \
  --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
/clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$build/legacy-check/bin/Release/net8.0/check.dll")" \
  "$(cygpath -m "$build/legacy/bin/Release/net8.0/System.ServiceModel.dll")" "$(cygpath -m "$here/legacy-forwards.json")"
