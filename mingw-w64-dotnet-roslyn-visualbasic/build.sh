#!/usr/bin/env bash
set -euo pipefail
source=$(cd "${1:?usage: build.sh SOURCE PREPARED}" && pwd)
out=$(cd "${2:?missing prepared}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export MSYS2_ARG_CONV_EXCL='*'
export DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
dotnet=${MINGW_PREFIX}/lib/dotnet/dotnet.exe
for tool in VBSyntaxGenerator VBErrorFactsGenerator BoundTreeGenerator;do
 extension=vbproj;[[ $tool != BoundTreeGenerator ]]||extension=csproj
 "$dotnet" build "$(cygpath -am "$out/$tool/Library.$extension")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
done
mkdir -p "$out/generated"
main="$source/src/Compilers/VisualBasic/Portable"
"$dotnet" "$(cygpath -am "$out/VBSyntaxGenerator/bin/Release/net8.0/VBSyntaxGenerator.dll")" "$(cygpath -am "$main/Syntax/Syntax.xml")" "$(cygpath -am "$out/generated")"
"$dotnet" "$(cygpath -am "$out/VBSyntaxGenerator/bin/Release/net8.0/VBSyntaxGenerator.dll")" "$(cygpath -am "$main/Syntax/Syntax.xml")" "$(cygpath -am "$out/generated")" /grammar
"$dotnet" "$(cygpath -am "$out/BoundTreeGenerator/bin/Release/net8.0/BoundTreeGenerator.dll")" VB "$(cygpath -am "$main/BoundTree/BoundNodes.xml")" "$(cygpath -am "$out/generated/BoundNodes.xml.Generated.vb")"
"$dotnet" "$(cygpath -am "$out/VBErrorFactsGenerator/bin/Release/net8.0/VBErrorFactsGenerator.dll")" "$(cygpath -am "$main/Errors/Errors.vb")" "$(cygpath -am "$out/generated/ErrorFacts.Generated.vb")"
/usr/bin/python3 - "$main/Generated" "$out/generated" <<'PY'
from pathlib import Path
import sys
expected,actual=(Path(p) for p in sys.argv[1:])
files=sorted(actual.iterdir());assert len(files)==6
for p in files:assert p.read_text(encoding='utf-8-sig')==(expected/p.name).read_text(encoding='utf-8-sig'),p.name
print('PASS all five original VB generated sources and grammar match the pinned source baseline')
PY
"$dotnet" pack "$(cygpath -am "$out/Microsoft.CodeAnalysis.VisualBasic/Library.vbproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -o "$(cygpath -am "$out/../feed")" -p:UseSharedCompilation=false -v:minimal
