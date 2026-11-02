"""Cold source preparation and evaluation using the source SDK8 API host."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';sdk=host.parent/'sdk/8.0.131';native=lambda p:Path(p).resolve().as_posix()
subprocess.run([sys.executable,'-X','utf8',here/'prepare.py',root/'nuget-sdk10-bf048eb7.tar.gz',root/'plan','--closure'],check=True)
tool=root/'evaluation';tool.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(here/'EvaluateProjects.cs'))
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    n=E.SubElement(ig,'Reference',Include=name);E.SubElement(n,'HintPath').text=native(sdk/(name+'.dll'))
E.ElementTree(p).write(tool/'Evaluate.csproj',encoding='utf-8',xml_declaration=True);(tool/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(tool/'cli-home'),NUGET_PACKAGES=native(tool/'cache'));commands=[]
for label,command in [('compile',[host,'build',tool/'Evaluate.csproj','-c','Release','--configfile',tool/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('evaluate',[host,tool/'bin/Release/net8.0/Evaluate.dll',root/'plan/wrappers.json',root/'plan/evaluated.json'])]:
    if label=='evaluate':env.update(MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'))
    with (tool/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(root/'prepare-results.json').write_text(json.dumps(dict(commands=commands,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NuGet7.3 VMR NET10 source evaluation')
