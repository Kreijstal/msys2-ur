#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir "${1:?usage: check.sh NEW_OUTPUT [COMPILER_DIRECTORY]}";out=$(cd "$1" && pwd)
tool=$(cd "${2:-${MINGW_PREFIX}/lib/dotnet/compiler-packs/roslyn-4.9.2}" && pwd)
export DOTNET_ROOT=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet) DOTNET_ROOT_X64=$(cygpath -am ${MINGW_PREFIX}/lib/dotnet)
export DOTNET_CLI_TELEMETRY_OPTOUT=1 MSBuildEnableWorkloadResolver=false DOTNET_CLI_HOME=$(cygpath -am "$out/cli-home") NUGET_PACKAGES=$(cygpath -am "$out/empty-packages")
compiler_root=${MINGW_PREFIX}/lib/dotnet/compiler-packs
mkdir -p "$compiler_root"
relocated=$(mktemp -d "$compiler_root/compiler check π.XXXXXX")
trap 'rm -rf "$relocated"' EXIT
cp -R "$tool/"* "$relocated/"
tool_native=$(cygpath -am "$relocated")
sdk_original=$(sha256sum ${MINGW_PREFIX}/lib/dotnet/sdk/8.0.131/Roslyn/bincore/csc.dll)
version=$(${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$tool_native/csc.dll" -version)
[[ $version == '4.9.2 (9934fb9e)'* ]]
mkdir "$out/probe" "$out/consumer"
cp "$here/Probe.cs" "$out/probe/"
cat > "$out/probe/Probe.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>Compiler49Probe</AssemblyName><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.9.2]"/></ItemGroup></Project>
PROJECT
cat > "$out/NuGet.config" <<CONFIG
<configuration><packageSources><clear/><add key="installed-source-built" value="$(cygpath -m ${MINGW_PREFIX}/lib/dotnet/library-packs)"/></packageSources></configuration>
CONFIG
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/probe/Probe.csproj")" -c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false -v:minimal
cat > "$out/consumer/Consumer.csproj" <<'PROJECT'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><RunAnalyzersDuringBuild>true</RunAnalyzersDuringBuild><WarningsAsErrors>CS9057;CS8032;AD0001</WarningsAsErrors><LangVersion>12.0</LangVersion><EmitCompilerGeneratedFiles>true</EmitCompilerGeneratedFiles></PropertyGroup><ItemGroup><Analyzer Include="../probe/bin/Release/net8.0/Compiler49Probe.dll"/></ItemGroup></Project>
PROJECT
cat > "$out/consumer/Program.cs" <<'CS'
using System;
class Program
{
 static int Main(){int[] values=[20,22];if(values[0]+values[1]!=GeneratedNumber.Value||GeneratedNumber.Compiler!="4.9.0.0")return 9;Console.WriteLine("PASS compiler49 generated value="+GeneratedNumber.Value+" compiler="+GeneratedNumber.Compiler);return 0;}
}
CS
args=(-c Release --configfile "$(cygpath -am "$out/NuGet.config")" -p:UseSharedCompilation=false "-p:CscToolPath=$tool_native" -p:CscToolExe=csc49.cmd -v:minimal)
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.csproj")" "${args[@]}"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$(cygpath -am "$out/consumer/bin/Release/net8.0/Consumer.dll")"
printf '%s\n' 'class Forbidden {}' > "$out/consumer/Negative.cs"
set +e
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.csproj")" "${args[@]}" > "$out/analyzer-negative.log" 2>&1
status=$?
set -e
[[ $status != 0 ]] && grep -q 'error CSC4901' "$out/analyzer-negative.log"
rm "$out/consumer/Negative.cs"
${MINGW_PREFIX}/lib/dotnet/dotnet.exe build "$(cygpath -am "$out/consumer/Consumer.csproj")" "${args[@]}"
# Direct command-line response file: Unicode source/output names and paths with spaces.
/usr/bin/python3 - "$out" ${MINGW_PREFIX}/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0 <<'PY'
from pathlib import Path
import sys,subprocess
out,refs=(Path(p) for p in sys.argv[1:]);source=out/'direct source π.cs';target=out/'direct output π.dll'
source.write_text('public class Number(int value) { public int Sum(){int[] a=[value,2];return a[0]+a[1];} }\n')
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
lines=['/noconfig','/nostdlib+','/target:library','/langversion:12','/deterministic+','/out:"'+native(target)+'"']
lines+=['/reference:"'+native(p)+'"' for p in sorted(refs.glob('*.dll'))];lines+=['"'+native(source)+'"']
(out/'response π.rsp').write_text('\n'.join(lines)+'\n',encoding='utf-8')
PY
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$tool_native/csc.dll" "@$(cygpath -am "$out/response π.rsp")"
[[ -s "$out/direct output π.dll" ]]
printf '%s\n' 'class Wrong { public int Get()=>"not an int"; }' > "$out/bad.cs"
set +e
${MINGW_PREFIX}/lib/dotnet/dotnet.exe "$tool_native/csc.dll" "@$(cygpath -am "$out/response π.rsp")" "$(cygpath -am "$out/bad.cs")" > "$out/compiler-negative.log" 2>&1
status=$?
set -e
[[ $status == 1 ]] && grep -q 'error CS0029' "$out/compiler-negative.log"
[[ $(sha256sum ${MINGW_PREFIX}/lib/dotnet/sdk/8.0.131/Roslyn/bincore/csc.dll) == "$sdk_original" ]]
printf '%s\n' 'PASS source csc49 CLI/version/CSharp12/Unicode-space RSP/error exit, relocated wrapper, actual MSBuild analyzer/incremental generator execution, and unchanged SDK compiler'
