"""Evaluate the original three source profiles using the installed source SDK8 MSBuild API."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
plan=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;out=plan/'evaluation';out.mkdir();native=lambda p:Path(p).resolve().as_posix()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';sdk=host.parent/'sdk/8.0.131';project=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='Evaluate',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable').items():E.SubElement(pg,k).text=v
ig=E.SubElement(project,'ItemGroup');E.SubElement(ig,'Compile',Include=native(here/'EvaluateProjects.cs'))
for n in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
 r=E.SubElement(ig,'Reference',Include=n);E.SubElement(r,'HintPath').text=native(sdk/(n+'.dll'))
E.ElementTree(project).write(out/'Evaluate.csproj',encoding='utf-8',xml_declaration=True);(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'),MSBuildExtensionsPath=native(sdk),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'empty-cache'))
for label,cmd in [('build',[host,'build',out/'Evaluate.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('evaluate',[host,out/'bin/Release/net8.0/Evaluate.dll',plan/'wrappers.json',plan/'evaluated.json'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 assert r.returncode==0,(label,r.returncode)
models=json.loads((plan/'evaluated.json').read_text());assert len(models)==7;print('PASS original NS2 options generator and six NET10 logging/options/DI libraries;compile items',sum(len(m['items']['Compile']) for m in models.values()))
