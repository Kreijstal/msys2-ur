#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$(cd "${1:?usage: pack.sh WCF_BUILD OUTPUT_FEED}" && pwd)
mkdir -p "${2:?missing output feed}"
feed=$(cd "$2" && pwd)
export DOTNET_ROOT=$(cygpath -m /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -m "$build/cli-home") NUGET_PACKAGES=$(cygpath -m "$build/empty-packages")
/usr/bin/python3 "$here/prepare-packages.py" "$build"
for name in System.Private.ServiceModel System.Web.Services.Description System.ServiceModel.{Primitives,Duplex,Security,Http,NetTcp}; do
  /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -m "$build/packages/pack.csproj")" -c Release \
    --configfile "$(cygpath -m "$build/NuGet.config")" -o "$(cygpath -m "$feed")" \
    -p:NuspecFile="$(cygpath -m "$build/packages/$name.nuspec")" \
    -p:NuspecBasePath="$(cygpath -m "$build/packages")" -p:UseSharedCompilation=false -v:minimal
done
