#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?usage: build-libraries.sh PREPARED}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -p:VbcToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2)" -p:VbcToolExe=vbc49.cmd -v:minimal)
for name in Microsoft.CodeAnalysis.CSharp.CodeStyle.Fixes Microsoft.CodeAnalysis.VisualBasic.CodeStyle.Fixes CodeStyleConfigFileGenerator;do
 suffix=csproj;[[ $name != *VisualBasic* ]] || suffix=vbproj
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/$name/Library.$suffix")" "${args[@]}"
done
for language in CSharp VisualBasic;do
 folder=$out/Microsoft.CodeAnalysis.$language.CodeStyle.Fixes/bin/Release/net8.0
 inputs="$(cygpath -am "$out/Microsoft.CodeAnalysis.CodeStyle/bin/Release/net8.0/Microsoft.CodeAnalysis.CodeStyle.dll");$(cygpath -am "$out/Microsoft.CodeAnalysis.$language.CodeStyle/bin/Release/net8.0/Microsoft.CodeAnalysis.$language.CodeStyle.dll")"
 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/CodeStyleConfigFileGenerator/bin/Release/net8.0/CodeStyleConfigFileGenerator.dll")" "$language" "$(cygpath -am "$folder")" "Microsoft.CodeAnalysis.$language.CodeStyle.targets" "$inputs"
done
