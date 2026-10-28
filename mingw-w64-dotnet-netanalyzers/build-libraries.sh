#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-libraries.sh PREPARED}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -p:VbcToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2)" -p:VbcToolExe=vbc49.cmd -v:minimal)
for name in Microsoft.CodeAnalysis.CSharp.NetAnalyzers Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers config-tool;do
 project=Library.csproj
 [[ $name != *VisualBasic* ]]||project=Library.vbproj
 [[ $name != config-tool ]]||project=Tool.csproj
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$name/$project")" "${args[@]}"
done
