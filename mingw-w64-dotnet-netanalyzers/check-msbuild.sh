#!/usr/bin/env bash
set -euo pipefail
consumer=$(cd "${1:?usage: check-msbuild.sh CONSUMER nuget|sdk}" && pwd);mode=${2:?}
[[ $mode == nuget || $mode == sdk ]]
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$consumer/cli-home") NUGET_PACKAGES=$(cygpath -am "$consumer/empty-packages")
for language in CSharp VisualBasic;do
 folder=$consumer/$mode-$language;mkdir "$folder"
 suffix=csproj;ext=cs;[[ $language != VisualBasic ]]||{ suffix=vbproj;ext=vb; }
 cp "$consumer/NuGet.config" "$folder/"
 cat > "$folder/.editorconfig" <<'CONFIG'
root = true
[*.{cs,vb}]
dotnet_diagnostic.CA1822.severity = error
CONFIG
 cat > "$folder/Probe.$suffix" <<XML
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><EnableNETAnalyzers>$([[ $mode == sdk ]]&&echo true||echo false)</EnableNETAnalyzers></PropertyGroup><ItemGroup><Compile Include="Probe.$ext"/>
XML
 if [[ $mode == nuget ]];then printf '<PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="[8.0.0-preview.26274.2]"/>\n' >> "$folder/Probe.$suffix";fi
 cat >> "$folder/Probe.$suffix" <<'XML'
</ItemGroup><Target Name="CaptureAnalyzerSelection" BeforeTargets="CoreCompile"><WriteLinesToFile File="$(MSBuildProjectDirectory)/analyzers.txt" Lines="@(Analyzer->'%(FullPath)')" Overwrite="true"/><WriteLinesToFile File="$(MSBuildProjectDirectory)/mode.txt" Lines="$(EnableNETAnalyzers)" Overwrite="true"/><WriteLinesToFile File="$(MSBuildProjectDirectory)/compiler.txt" Lines="$(CscToolPath);$(CscToolExe);$(VbcToolPath);$(VbcToolExe)" Overwrite="true"/></Target></Project>
XML
 if [[ $language == CSharp ]];then printf 'public class Probe { public int M()=>42; }\n' > "$folder/Probe.cs";else printf 'Public Class Probe\n Public Function M() As Integer\n Return 42\n End Function\nEnd Class\n' > "$folder/Probe.vb";fi
 args=(-c Release --configfile "$(cygpath -am "$folder/NuGet.config")" -p:UseSharedCompilation=false -v:minimal)
 if [[ $mode == nuget ]];then
  args+=(-p:CscToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -p:VbcToolPath="$(cygpath -am ${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-vb-4.9.2)" -p:VbcToolExe=vbc49.cmd)
 fi
 set +e
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$folder/Probe.$suffix")" "${args[@]}" > "$folder/negative.log" 2>&1
 result=$?
 set -e
 [[ $result -ne 0 ]]&&grep -q 'error CA1822' "$folder/negative.log"
 if [[ $language == CSharp ]];then sed -i 's/public int M/public static int M/' "$folder/Probe.cs";else sed -i 's/Public Function M/Public Shared Function M/' "$folder/Probe.vb";fi
 ${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$folder/Probe.$suffix")" "${args[@]}" > "$folder/corrected.log" 2>&1
 python3 - "$folder" "$language" "$mode" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);language=sys.argv[2];mode=sys.argv[3]
files=[s for s in (p/'analyzers.txt').read_text(encoding='utf-8-sig').splitlines() if 'NetAnalyzers' in s and s.endswith('.dll')]
assert len(files)==2,files
assert {Path(s.replace('\\','/')).name for s in files}=={'Microsoft.CodeAnalysis.NetAnalyzers.dll','Microsoft.CodeAnalysis.'+language+'.NetAnalyzers.dll'},files
assert (p/'mode.txt').read_text(encoding='utf-8-sig').strip()==('true' if mode=='sdk' else 'false')
if mode=='sdk':
 assert all('/sdk/8.0.131/sdks/microsoft.net.sdk/analyzers/' in s.replace('\\','/').lower() for s in files)
 compiler=(p/'compiler.txt').read_text(encoding='utf-8-sig');assert ('csc49.cmd' if language=='CSharp' else 'vbc49.cmd') in compiler,compiler
for log in ['negative.log','corrected.log']:assert 'CS9057' not in (p/log).read_text() and 'AD0001' not in (p/log).read_text()
print('PASS',language,mode,'selects exactly2 source analyzer DLLs; CA1822 negative rejected and static/Shared correction builds through source compiler')
PY
done
