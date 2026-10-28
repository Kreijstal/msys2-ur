#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED] [DATA_DIRECTORY]}";out=$(cd "$1" && pwd)
data=$(cd "${3:-/clang64/share/doc/dotnet-codeanalysis-analyzers}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cp "$here/Check.cs" "$out/Program.cs";cp "$here/CheckSpecialFixes.cs" "$out/"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ -n ${2:-} ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources></configuration>\n' >> "$out/NuGet.config"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><RunAnalyzersDuringBuild>false</RunAnalyzersDuringBuild><EnableDefaultCompileItems>false</EnableDefaultCompileItems><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><Compile Include="CheckSpecialFixes.cs"/><PackageReference Include="Microsoft.CodeAnalysis.Analyzers" Version="[3.3.4]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/><PackageReference Include="Microsoft.CodeAnalysis.VisualBasic.Workspaces" Version="[4.9.2]"/><None Include="payload/**/*.dll" Link="%(RecursiveDir)%(Filename)%(Extension)" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Check.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
/usr/bin/python3 - "$out" "$data" <<'PY'
from pathlib import Path
import hashlib,json,sys,zipfile
out,data=(Path(p) for p in sys.argv[1:]);cache=out/'empty-packages/microsoft.codeanalysis.analyzers/3.3.4'
with zipfile.ZipFile(cache/'microsoft.codeanalysis.analyzers.3.3.4.nupkg') as z:
 dlls=[n for n in z.namelist() if n.endswith('.dll')];assert len(dlls)==30
 for file in dlls:
  if file.startswith('analyzers/dotnet/vb/') and not file.endswith('/Microsoft.CodeAnalysis.VisualBasic.Analyzers.dll'):
   assert z.read(file)==z.read(file.replace('/vb/','/cs/',1)),file
 for file in dlls:
  if file.startswith('analyzers/dotnet/vb/') and not file.endswith('/Microsoft.CodeAnalysis.VisualBasic.Analyzers.dll'):continue
  relative=Path(file).relative_to('analyzers/dotnet/'+('vb' if '/vb/' in file else 'cs'))
  target=out/'payload'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(file))
 expected=json.loads((data/'ExpectedGeneratedAssets.json').read_text())['normalized_sha256']
 for file,sha in expected.items():assert hashlib.sha256(z.read(file).replace(b'\r\n',b'\n')).hexdigest()==sha,file
 assert len(expected)==554
print('PASS NuGet language/satellite asset layout, identical shared copies and all 554 independently baselined configuration/documentation assets')
PY
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --no-restore -p:UseSharedCompilation=false -v:minimal
timeout 240 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$data/ExpectedInventory.json")" "$(cygpath -am "$data/localization.json")" "$(cygpath -am "$data/fixtures.json")" "$(cygpath -am /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$out/fixture-results.json")"
bash "$here/check-api.sh" "$out" "$out/metadata-check"
# Actual NuGet/MSBuild language asset selection and live diagnostics through source 4.9 hosts.
for language in cs vb;do
 mkdir "$out/sample-$language"
 extension=csproj;host=Csc;wrapper=csc49.cmd;compiler=/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2
 if [[ $language == vb ]];then extension=vbproj;host=Vbc;wrapper=vbc49.cmd;compiler=/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2;fi
 cat > "$out/sample-$language/Sample.$extension" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><RootNamespace></RootNamespace><EnableNETAnalyzers>false</EnableNETAnalyzers><RunAnalyzersDuringBuild>true</RunAnalyzersDuringBuild><NuGetAudit>false</NuGetAudit><WarningsAsErrors>CS9057;CS8032;BC42507;BC42376;AD0001</WarningsAsErrors></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.Analyzers" Version="[3.3.4]"/><PackageReference Include="Microsoft.CodeAnalysis.Common" Version="[4.9.2]"/></ItemGroup><Target Name="CaptureOwnedAnalyzerSelection" AfterTargets="ResolveReferences"><WriteLinesToFile File="$(MSBuildProjectDirectory)/selected-analyzers.txt" Lines="@(Analyzer)" Overwrite="true"/></Target></Project>
PROJECT
 printf 'root = true\n[*]\ndotnet_diagnostic.RS1026.severity = error\n' > "$out/sample-$language/.editorconfig"
 if [[ $language == cs ]];then
  cat > "$out/sample-$language/Sample.cs" <<'CS'
using System.Collections.Immutable;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class Owned : DiagnosticAnalyzer {
 public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics => ImmutableArray<DiagnosticDescriptor>.Empty;
 public override void Initialize(AnalysisContext context) { context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None); }
}
CS
 else
  cat > "$out/sample-$language/Sample.vb" <<'VB'
Imports System.Collections.Immutable
Imports Microsoft.CodeAnalysis
Imports Microsoft.CodeAnalysis.Diagnostics
<DiagnosticAnalyzer(LanguageNames.VisualBasic)>
Public Class Owned
 Inherits DiagnosticAnalyzer
 Public Overrides ReadOnly Property SupportedDiagnostics As ImmutableArray(Of DiagnosticDescriptor)
  Get
   Return ImmutableArray(Of DiagnosticDescriptor).Empty
  End Get
 End Property
 Public Overrides Sub Initialize(context As AnalysisContext)
  context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None)
 End Sub
End Class
VB
 fi
 args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false "-p:${host}ToolPath=$(cygpath -am "$compiler")" "-p:${host}ToolExe=$wrapper" -v:minimal)
 set +e
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/sample-$language/Sample.$extension")" "${args[@]}" > "$out/$language-negative.log" 2>&1
 status=$?
 set -e
 [[ $status != 0 ]] && grep -q 'error RS1026' "$out/$language-negative.log"
 /usr/bin/python3 - "$out/sample-$language/Sample.$language" "$language" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();old='context.ConfigureGeneratedCodeAnalysis'
s=s.replace(old,'context.EnableConcurrentExecution(); '+old if sys.argv[2]=='cs' else 'context.EnableConcurrentExecution()\n  '+old)
p.write_text(s)
PY
 /clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/sample-$language/Sample.$extension")" "${args[@]}"
 /usr/bin/python3 - "$out/sample-$language/selected-analyzers.txt" "$language" <<'PY'
from pathlib import Path
import sys
paths=[p.replace('\\','/') for p in Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines() if '/microsoft.codeanalysis.analyzers/' in p.replace('\\','/').lower()]
name='CSharp' if sys.argv[2]=='cs' else 'VisualBasic'
assert len(paths)==2,paths
assert {Path(p).name for p in paths}=={'Microsoft.CodeAnalysis.Analyzers.dll','Microsoft.CodeAnalysis.'+name+'.Analyzers.dll'},paths
assert all('/analyzers/dotnet/'+sys.argv[2]+'/' in p for p in paths),paths
print('PASS real '+name+' NuGet/MSBuild asset selection, expected RS1026 failure and corrected success through installed source compiler49')
PY
done
/usr/bin/python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,sys,zipfile
out=Path(sys.argv[1]);hashes={}
with zipfile.ZipFile(out/'empty-packages/microsoft.codeanalysis.analyzers/3.3.4/microsoft.codeanalysis.analyzers.3.3.4.nupkg') as z:
 for file in z.namelist():
  if not file.endswith('.dll'):continue
  relative=Path(file).relative_to('analyzers/dotnet/'+('vb' if '/vb/' in file else 'cs'));data=z.read(file)
  assert (out/'bin/Release/net8.0'/relative).read_bytes()==data,file
  hashes[file]=hashlib.sha256(data).hexdigest()
(out/'payload-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
report=json.loads((out/'fixture-results.json').read_text());assert len(report['passed'])==78 and not report['failures'] and len(report['code_fixes'])==13
print('PASS all 30 NuGet DLL assets match the sixteen tested implementation/satellite DLLs exactly; all 78 cases and 13 code-fix providers pass')
PY
