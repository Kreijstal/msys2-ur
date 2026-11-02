"""Prepare a cold MSBuild18 build using pinned source archives and source SDK8."""
from pathlib import Path
import json,os,shutil,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet/dotnet.exe';sdk=host.parent/'sdk/8.0.131';native=lambda p:Path(p).resolve().as_posix()
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'empty-packages'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
commands=[]
def run(label,command):
    with (root/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('prepare-plan',[sys.executable,'-X','utf8',here/'prepare-plan.py',root/'msbuild-sdk10-228caa11.tar.gz',root/'plan'])
feed=root/'msbuild-source-packages';feed.mkdir()
for p in root.glob('microsoft.codeanalysis.*.nupkg'):shutil.copyfile(p,feed/p.name)
assert len(list(feed.glob('*.nupkg')))==3
tool=root/'evaluation-tool';tool.mkdir()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='EvaluateProjects',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(here/'EvaluateProjects.cs'))
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    r=E.SubElement(ig,'Reference',Include=name);E.SubElement(r,'HintPath').text=native(sdk/(name+'.dll'))
E.ElementTree(p).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
(tool/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('build-evaluator',[host,'build',tool/'Build.csproj','-c','Release','--configfile',tool/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
env.update(MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'))
run('evaluate',[host,tool/'bin/Release/net8.0/EvaluateProjects.dll',root/'plan/wrappers.json',root/'plan/evaluated.json'])
model=json.loads((root/'plan/evaluated.json').read_text());assert len(model)==6
assert sum(len(e['items']['Compile']) for e in model.values())==1326
(root/'prepare-results.json').write_text(json.dumps(dict(commands=commands,original_net10_projects=6,original_compile_items=1326,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS cold source MSBuild18 preparation and original six-project evaluation')
