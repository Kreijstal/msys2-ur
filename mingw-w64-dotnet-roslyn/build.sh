#!/usr/bin/env bash
set -euo pipefail
source_root=$(cd "${1:?usage: build.sh SOURCE PREPARED_OUTPUT}" && pwd)
output=$(cd "${2:?usage: build.sh SOURCE PREPARED_OUTPUT}" && pwd)
export PATH=${MINGW_PREFIX}/bin:/usr/bin:$PATH
export DOTNET_ROOT=$(cygpath -m ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT MSBuildEnableWorkloadResolver=false
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME=$(cygpath -m "$output/cli-home")
export NUGET_PACKAGES=$(cygpath -m "$output/empty-packages")
dotnet=${MINGW_PREFIX}/lib/dotnet/dotnet.exe
for generator in CSharpSyntaxGenerator BoundTreeGenerator CSharpErrorFactsGenerator; do
  "$dotnet" build "$(cygpath -m "$output/$generator/build.csproj")" -c Release \
    --configfile "$(cygpath -m "$output/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
mkdir "$output/generated"
"$dotnet" "$(cygpath -m "$output/CSharpSyntaxGenerator/bin/Release/net8.0/CSharpSyntaxGenerator.dll")" \
  "$(cygpath -m "$source_root/src/Compilers/CSharp/Portable/Syntax/Syntax.xml")" "$(cygpath -m "$output/generated")"
"$dotnet" "$(cygpath -m "$output/BoundTreeGenerator/bin/Release/net8.0/BoundTreeGenerator.dll")" \
  CSharp "$(cygpath -m "$source_root/src/Compilers/CSharp/Portable/BoundTree/BoundNodes.xml")" \
  "$(cygpath -m "$output/generated/BoundNodes.xml.Generated.cs")"
"$dotnet" "$(cygpath -m "$output/CSharpErrorFactsGenerator/bin/Release/net8.0/CSharpErrorFactsGenerator.dll")" \
  "$(cygpath -m "$source_root/src/Compilers/CSharp/Portable/Errors/ErrorCode.cs")" \
  "$(cygpath -m "$output/generated/ErrorFacts.Generated.cs")"
/usr/bin/python3 "$(dirname "$0")/check-generated.py" "$source_root" "$output/generated"
for assembly in Microsoft.CodeAnalysis Microsoft.CodeAnalysis.CSharp; do
  "$dotnet" pack "$(cygpath -m "$output/$assembly/build.csproj")" -c Release \
    -o "$(cygpath -m "$output/feed")" --configfile "$(cygpath -m "$output/NuGet.config")" \
    -p:RestoreSources="$(cygpath -m "$output/feed")" -p:UseSharedCompilation=false -v:minimal
done
