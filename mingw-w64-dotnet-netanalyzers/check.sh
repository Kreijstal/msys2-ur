#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [NEW_FEED] [DATA_DIRECTORY]}";out=$(cd "$1" && pwd)
data=$(cd "${3:-/clang64/share/doc/dotnet-netanalyzers}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false
export DOTNET_ROOT_X64=$DOTNET_ROOT DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
cp "$here/Check.cs" "$out/Program.cs"
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source" value="$(cygpath -am /clang64/lib/dotnet/library-packs)"/>
CONFIG
if [[ -n ${2:-} ]];then printf '<add key="new-source" value="%s"/>\n' "$(cygpath -am "$2")" >> "$out/NuGet.config";fi
printf '</packageSources></configuration>\n' >> "$out/NuGet.config"
cat > "$out/Check.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><RunAnalyzersDuringBuild>false</RunAnalyzersDuringBuild><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="[8.0.0-preview.26274.2]"/><PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="[4.9.2]"/><PackageReference Include="Microsoft.CodeAnalysis.VisualBasic.Workspaces" Version="[4.9.2]"/><None Include="payload/**/*.dll" Link="%(RecursiveDir)%(Filename)%(Extension)" CopyToOutputDirectory="PreserveNewest"/></ItemGroup></Project>
PROJECT
/clang64/lib/dotnet/dotnet.exe restore "$(cygpath -am "$out/Check.csproj")" --configfile "$(cygpath -am "$out/NuGet.config")" -v:minimal
/usr/bin/python3 - "$out" "$data" <<'PY'
from pathlib import Path
import hashlib,json,sys,zipfile
out,data=(Path(p) for p in sys.argv[1:]);cache=out/'empty-packages/microsoft.codeanalysis.netanalyzers/8.0.0-preview.26274.2'
with zipfile.ZipFile(cache/'microsoft.codeanalysis.netanalyzers.8.0.0-preview.26274.2.nupkg') as z:
 dlls=[n for n in z.namelist() if n.endswith('.dll')];assert len(dlls)==30
 for file in dlls:
  if file.startswith('analyzers/dotnet/vb/') and not file.endswith('/Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers.dll'):
   assert z.read(file)==z.read(file.replace('/vb/','/cs/',1)),file
 for file in dlls:
  if file.startswith('analyzers/dotnet/vb/') and not file.endswith('/Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers.dll'):continue
  relative=Path(file).relative_to('analyzers/dotnet/'+('vb' if '/vb/' in file else 'cs'))
  target=out/'payload'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(file))
 expected=json.loads((data/'ExpectedGeneratedAssets.json').read_text())
 for file,text in expected.items():assert z.read(file).decode('utf-8-sig').replace('\r\n','\n')==text,file
 assert len(expected)==611
print('PASS30 NuGet DLL assets, identical shared copies and all611 published configuration/documentation assets')
PY
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/Check.csproj")" -c Release --no-restore -p:UseSharedCompilation=false -p:CscToolPath="$(cygpath -am /clang64/lib/dotnet/compiler-packs/roslyn-4.9.2)" -p:CscToolExe=csc49.cmd -v:minimal
timeout 600 /clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/bin/Release/net8.0/Check.dll")" "$(cygpath -am "$data/ExpectedAssemblies.json")" "$(cygpath -am "$data/localization.json")" "$(cygpath -am "$data/fixtures.json")" "$(cygpath -am /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0)" "$(cygpath -am "$data/ExpectedLegacyEmpty.json")" "$(cygpath -am /ucrt64/lib/mono/4.7.2-api)"
bash "$here/check-api.sh" "$out" "$out/metadata-check"

bash "$here/check-msbuild.sh" "$out" nuget
