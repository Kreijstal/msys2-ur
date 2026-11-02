"""Build and run the project evaluator using declared installed source tools."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
root,out=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
 p=Path(p).resolve()
 if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
 return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap');sdk=Path('/clang64/lib/dotnet/sdk/8.0.131');sdk_native=native(sdk)
tool=out/'evaluation-tool';tool.mkdir();tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='EvaluateRoslynProjects',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',CscToolPath=native(compiler),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/EvaluateRoslynProjects.cs'))
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:E.SubElement(E.SubElement(items,'Reference',Include=name),'HintPath').text=sdk_native+'/'+name+'.dll'
E.indent(tree);E.ElementTree(tree).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe'
with (out/'evaluation-build.log').open('w') as log:subprocess.run([dotnet,'build',native(tool/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
env.update(MSBuildSDKsPath=sdk_native+'/Sdks',MSBUILD_EXE_PATH=sdk_native+'/MSBuild.dll')
with (out/'evaluation.log').open('w') as log:subprocess.run([dotnet,native(tool/'bin/Release/net8.0/EvaluateRoslynProjects.dll'),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
