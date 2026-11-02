#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?OUTPUT}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/cache")
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
for name in Framework10.Arcade.Resources ILLink.Tasks;do
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/tools/$name/Build.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal >"$out/tools/$name/build.log" 2>&1
done
mkdir "$out/tools/net"
cp /clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/* "$out/tools/net/"
cp "$out/tools/ILLink.Tasks/bin/Release/net8.0/ILLink.Tasks.dll" "$out/tools/net/"
printf '%s\n' 'PASS original resource generator and complete original ILLink tasks built for NET8 host'
