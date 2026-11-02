#!/usr/bin/env bash
set -euo pipefail
consumer=$(cd "${1:?usage: check-msbuild.sh CONSUMER nuget|sdk}" && pwd);mode=${2:?}
[[ $mode == nuget || $mode == sdk ]]
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$consumer/cli-home") NUGET_PACKAGES=$(cygpath -am "$consumer/empty-packages")
for language in CSharp VisualBasic;do
 folder=$consumer/$mode-$language;mkdir "$folder"
 suffix=csproj;ext=cs;[[ $language != VisualBasic ]] || { suffix=vbproj;ext=vb; }
 cp "$consumer/NuGet.config" "$folder/"
 cat > "$folder/.editorconfig" <<'CONFIG'
root = true
[*.{cs,vb}]
dotnet_style_readonly_field = true:warning
dotnet_diagnostic.IDE0044.severity = error
CONFIG
 cat > "$folder/Probe.$suffix" <<XML
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><EnforceCodeStyleInBuild>$([[ $mode == sdk ]] && echo true || echo false)</EnforceCodeStyleInBuild></PropertyGroup><ItemGroup><Compile Include="Probe.$ext"/>
XML
 if [[ $mode == nuget ]];then printf '<PackageReference Include="Microsoft.CodeAnalysis.%s.CodeStyle" Version="[4.9.2]"/>\n' "$language" >> "$folder/Probe.$suffix";fi
 cat >> "$folder/Probe.$suffix" <<'XML'
</ItemGroup><Target Name="CaptureAnalyzerSelection" BeforeTargets="CoreCompile"><WriteLinesToFile File="$(MSBuildProjectDirectory)/analyzers.txt" Lines="@(Analyzer->'%(FullPath)')" Overwrite="true"/><WriteLinesToFile File="$(MSBuildProjectDirectory)/mode.txt" Lines="$(EnforceCodeStyleInBuild)" Overwrite="true"/></Target></Project>
XML
 if [[ $language == CSharp ]];then
  printf 'class Probe { private int n=1; public int M()=>n; }\n' > "$folder/Probe.cs"
 else
  printf 'Class Probe\n Private n As Integer = 1\n Public Function M() As Integer\n Return n\n End Function\nEnd Class\n' > "$folder/Probe.vb"
 fi
 args=(-c Release --configfile "$(cygpath -am "$folder/NuGet.config")" -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -p:VbcToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-vb-4.9.2)" -p:VbcToolExe=vbc49.cmd -v:minimal)
 set +e
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$folder/Probe.$suffix")" "${args[@]}" > "$folder/negative.log" 2>&1
 result=$?
 set -e
 [[ $result -ne 0 ]] && grep -q 'error IDE0044' "$folder/negative.log"
 if [[ $language == CSharp ]];then sed -i 's/private int n/private readonly int n/' "$folder/Probe.cs";else sed -i 's/Private n/Private ReadOnly n/' "$folder/Probe.vb";fi
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$folder/Probe.$suffix")" "${args[@]}" > "$folder/corrected.log" 2>&1
 python3 - "$folder" "$language" "$mode" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);language=sys.argv[2];mode=sys.argv[3]
files=[s for s in (p/'analyzers.txt').read_text(encoding='utf-8-sig').splitlines() if 'CodeStyle' in s and s.endswith('.dll')]
assert len(files)==4,files
assert set(Path(s.replace('\\','/')).name for s in files)=={'Microsoft.CodeAnalysis.CodeStyle.dll','Microsoft.CodeAnalysis.CodeStyle.Fixes.dll','Microsoft.CodeAnalysis.'+language+'.CodeStyle.dll','Microsoft.CodeAnalysis.'+language+'.CodeStyle.Fixes.dll'},files
assert (p/'mode.txt').read_text(encoding='utf-8-sig').strip()==('true' if mode=='sdk' else 'false')
assert all(('codestyle/'+('cs' if language=='CSharp' else 'vb')+'/') in s.replace('\\','/').lower() for s in files) if mode=='sdk' else all(('microsoft.codeanalysis.'+language.lower()+'.codestyle/4.9.2/analyzers/dotnet/') in s.replace('\\','/').lower() for s in files)
print('PASS',language,mode,'selects exactly4 source analyzer/fixer DLLs; IDE0044 negative rejected and readonly correction builds')
PY
done
