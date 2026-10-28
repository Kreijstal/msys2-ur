#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [COMPILER_DIRECTORY]}";out=$(cd "$1" && pwd)
tool=$(cd "${2:-/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2}" && pwd)
export DOTNET_ROOT=$(cygpath -am /clang64/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am /clang64/lib/dotnet)
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
compiler_root=/clang64/lib/dotnet/compiler-packs
mkdir -p "$compiler_root"
relocated=$(mktemp -d "$compiler_root/compiler check π.XXXXXX")
trap 'rm -rf "$relocated"' EXIT
cp -R "$tool/"* "$relocated/"
tool_native=$(cygpath -am "$relocated")
sdk_original=$(sha256sum /clang64/lib/dotnet/sdk/8.0.131/Roslyn/bincore/vbc.dll)
version=$(/clang64/lib/dotnet/dotnet.exe "$tool_native/vbc.dll" -version)
[[ $version == '4.9.2 (9934fb9e)'* ]]
mkdir "$out/probe" "$out/consumer"
cp "$here/Probe.cs" "$out/probe/"
cat > "$out/probe/Probe.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>VbCompiler49Probe</AssemblyName><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.VisualBasic" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source-built" value="$(cygpath -m /clang64/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/probe/Probe.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
cat > "$out/consumer/Consumer.vbproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><RootNamespace></RootNamespace><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><RunAnalyzersDuringBuild>true</RunAnalyzersDuringBuild><WarningsAsErrors>BC42507;BC42376;AD0001</WarningsAsErrors><EmitCompilerGeneratedFiles>true</EmitCompilerGeneratedFiles></PropertyGroup><ItemGroup><Analyzer Include="../probe/bin/Release/net8.0/VbCompiler49Probe.dll"/></ItemGroup></Project>
PROJECT
cat > "$out/consumer/Program.vb" <<'VB'
Imports System
Module Program
 Function Main() As Integer
  If GeneratedNumber.Value <> 42 OrElse GeneratedNumber.Compiler <> "4.9.0.0" Then Return 9
  Console.WriteLine("PASS vbc49 generated value=" & GeneratedNumber.Value & " compiler=" & GeneratedNumber.Compiler)
  Return 0
 End Function
End Module
VB
args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false "-p:VbcToolPath=$tool_native" -p:VbcToolExe=vbc49.cmd -v:minimal)
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.vbproj")" "${args[@]}"
/clang64/lib/dotnet/dotnet.exe "$(cygpath -am "$out/consumer/bin/Release/net8.0/Consumer.dll")"
printf '%s\n' 'Class Forbidden' 'End Class' > "$out/consumer/Negative.vb"
set +e
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.vbproj")" "${args[@]}" > "$out/analyzer-negative.log" 2>&1
status=$?
set -e
[[ $status != 0 ]] && grep -q 'error VBC4901' "$out/analyzer-negative.log"
rm "$out/consumer/Negative.vb"
/clang64/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.vbproj")" "${args[@]}"
# Direct command-line response file: Unicode source/output names and paths with spaces.
/usr/bin/python3 - "$out" /clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0 <<'PY'
from pathlib import Path
import sys,subprocess
out,refs=(Path(p) for p in sys.argv[1:]);source=out/'direct source π.vb';target=out/'direct output π.dll'
source.write_text('Public Class Number\n Public Function Sum() As Integer\n Return 42\n End Function\nEnd Class\n')
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
lines=['/nostdlib','/target:library','/vbruntime*','/optionstrict+','/deterministic+','/out:"'+native(target)+'"']
lines+=['/reference:"'+native(p)+'"' for p in sorted(refs.glob('*.dll'))];lines+=['"'+native(source)+'"']
(out/'response π.rsp').write_text('\n'.join(lines)+'\n',encoding='utf-8')
PY
/clang64/lib/dotnet/dotnet.exe "$tool_native/vbc.dll" -noconfig "@$(cygpath -am "$out/response π.rsp")"
[[ -s "$out/direct output π.dll" ]]
printf '%s\n' 'Class Wrong' 'Function GetValue() As Integer' 'Return "bad"' 'End Function' 'End Class' > "$out/bad.vb"
set +e
/clang64/lib/dotnet/dotnet.exe "$tool_native/vbc.dll" -noconfig "@$(cygpath -am "$out/response π.rsp")" "$(cygpath -am "$out/bad.vb")" > "$out/compiler-negative.log" 2>&1
status=$?
set -e
[[ $status == 1 ]] && grep -q 'error BC30512' "$out/compiler-negative.log"
[[ $(sha256sum /clang64/lib/dotnet/sdk/8.0.131/Roslyn/bincore/vbc.dll) == "$sdk_original" ]]
printf '%s\n' 'PASS source vbc49 CLI/version/VisualBasic/Unicode-space RSP/error exit, relocated wrapper, actual MSBuild analyzer/incremental generator execution, and unchanged SDK compiler'
