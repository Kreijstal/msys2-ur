#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: check-api.sh PREPARED_ROOT CONSUMER_ROOT NEW_OUTPUT [CONSUMER_FRAMEWORK]}" && pwd)
consumer=$(cd "${2:?missing consumer}" && pwd)
mkdir "${3:?missing output}"
out=$(cd "$3" && pwd)
framework=${4:-net8.0}
test -f "$consumer/bin/Release/$framework/System.Data.SqlClient.dll"
cp "$here/CheckApi.cs" "$out/Program.cs"
cat > "$out/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$out/cli-home") NUGET_PACKAGES=$(cygpath -m "$out/empty-packages")
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -m "$out/check.csproj")" -c Release --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -m "$out/bin/Release/net8.0/check.dll")" \
  "$(cygpath -m "$build/contract/bin/Release/net8.0/System.Data.SqlClient.dll")" \
  "$(cygpath -m "$consumer/bin/Release/$framework")" "$(cygpath -m "$consumer/bin/Release/$framework")"
