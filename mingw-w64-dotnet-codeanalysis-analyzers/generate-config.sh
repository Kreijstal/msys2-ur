#!/usr/bin/env bash
set -euo pipefail
prepared=$(cd "${1:?usage: generate-config.sh PREPARED SOURCE}" && pwd)
source=$(cd "${2:?missing original source}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT MSYS2_ARG_CONV_EXCL='*'
generated=$prepared/generated
mkdir "$generated"
for language in Core CSharp VisualBasic;do
 name=Microsoft.CodeAnalysis.Analyzers
 [[ $language != CSharp ]]||name=Microsoft.CodeAnalysis.CSharp.Analyzers
 [[ $language != VisualBasic ]]||name=Microsoft.CodeAnalysis.VisualBasic.Analyzers
 target=$generated/inputs/$name/Release/net8.0
 mkdir -p "$target/AnalyzerReleases/$name"
 cp "$prepared/$name/bin/Release/net8.0/$name.dll" "$target/"
 for file in AnalyzerReleases.Shipped.md AnalyzerReleases.Unshipped.md;do cp "$source/src/Microsoft.CodeAnalysis.Analyzers/$language/$file" "$target/AnalyzerReleases/$name/";done
done
for culture in cs de es fr it ja ko pl pt-BR ru tr zh-Hans zh-Hant;do
 mkdir "$generated/inputs/Microsoft.CodeAnalysis.Analyzers/Release/net8.0/$culture"
 cp "$prepared/Microsoft.CodeAnalysis.Analyzers/bin/Release/net8.0/$culture/Microsoft.CodeAnalysis.Analyzers.resources.dll" "$generated/inputs/Microsoft.CodeAnalysis.Analyzers/Release/net8.0/$culture/"
done
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$prepared/config-tool/bin/Release/net8.0/Tool.dll")" \
 -validateOnly:false "$(cygpath -am "$generated/rulesets")" "$(cygpath -am "$generated/editorconfig")" "$(cygpath -am "$generated/globalconfig")" \
 "$(cygpath -am "$generated/inputs")" Release net8.0 'Microsoft.CodeAnalysis.Analyzers.dll;Microsoft.CodeAnalysis.CSharp.Analyzers.dll;Microsoft.CodeAnalysis.VisualBasic.Analyzers.dll' \
 "$(cygpath -am "$generated/buildTransitive")" Microsoft.CodeAnalysis.Analyzers.props "$(cygpath -am "$generated/buildTransitive")" Microsoft.CodeAnalysis.Analyzers.targets '' \
 "$(cygpath -am "$generated/docs")" Microsoft.CodeAnalysis.Analyzers.md "$(cygpath -am "$generated/docs")" Microsoft.CodeAnalysis.Analyzers.sarif \
 3.3.4 Microsoft.CodeAnalysis.Analyzers false false false true
