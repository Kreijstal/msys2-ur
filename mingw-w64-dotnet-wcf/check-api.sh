#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: check-api.sh WCF_BUILD IMPLEMENTATION_ASSETS}" && pwd)
implementation=$(cd "${2:?usage: check-api.sh WCF_BUILD IMPLEMENTATION_ASSETS}" && pwd)
export PATH=/clang64/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
mkdir -p "$build/runtime-assets" "$build/api-check"
cp "$implementation"/*.dll "$build/runtime-assets/"
for name in Primitives Duplex Security Http NetTcp; do
  cp "$build/facades/System.ServiceModel.$name/bin/Release/net8.0/System.ServiceModel.$name.dll" "$build/runtime-assets/"
done
cp "$here/CheckApi.cs" "$build/api-check/"
cat > "$build/api-check/check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -m "$build/api-check/check.csproj")" -c Release \
  --configfile "$(cygpath -m "$build/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
overall=0
for name in Primitives Duplex Security Http NetTcp; do
  status=0
  /clang64/lib/dotnet/dotnet.exe "$(cygpath -m "$build/api-check/bin/Release/net8.0/check.dll")" \
    "$(cygpath -m "$build/contract-assets/System.ServiceModel.$name.dll")" \
    "$(cygpath -m "$build/runtime-assets")" "$(cygpath -m "$build/runtime-assets")" \
    "$(cygpath -m "$here/upstream-api-mismatches.json")" || status=$?
  echo "API $name: exit $status"
  [[ $status == 0 ]] || overall=1
done
exit "$overall"
