#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$1" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT
export DOTNET_CLI_HOME=$(cygpath -am "$root/archive-cli-home")
export NUGET_PACKAGES=$(cygpath -am "$root/archive-cache")
export MSBuildEnableWorkloadResolver=false DOTNET_CLI_TELEMETRY_OPTOUT=1
for name in Microsoft.Win32.Registry System.Text.Encoding.CodePages;do
 /clang64/lib/dotnet/dotnet.exe pack "$(cygpath -am "$root/$name/archive/Archive.csproj")" -c Release --configfile "$(cygpath -am "$root/NuGet.config")" -p:UseSharedCompilation=false -o "$(cygpath -am "$root/feed")" -v:minimal
done
