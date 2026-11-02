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
run('prepare-plan',[sys.executable,'-X','utf8',here/'prepare-plan.py',root/'msbuild-17.11.48-02bf6629.tar.gz',root/'plan17','--msbuild-17.11-net8'])
feed=root/'msbuild1711-source-packages';feed.mkdir()
for p in root.glob('microsoft.codeanalysis.*.nupkg'):shutil.copyfile(p,feed/p.name)
assert len(list(feed.glob('*.nupkg')))==1
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
run('evaluate',[host,tool/'bin/Release/net8.0/EvaluateProjects.dll',root/'plan17/wrappers.json',root/'plan17/evaluated.json'])
model=json.loads((root/'plan17/evaluated.json').read_text());assert len(model)==6
assert sum(len(e['items']['Compile']) for e in model.values())==1195
(root/'prepare-results.json').write_text(json.dumps(dict(commands=commands,original_net10_projects=6,original_compile_items=1195,full_dependency_goal_complete=False),indent=2)+'\n')
roslyn=root/'roslyn-source'
roslyn.mkdir()
import tarfile,hashlib
archive=root/'roslyn-sdk10-2333221c.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e28cee5a55aaceccb555c8e1b583a8877d88002dde2468801b8d3f17463f2efb'
selected=('eng/','src/Compilers/Core/MSBuildTask/','src/Compilers/Core/Portable/','src/Compilers/Shared/','src/Dependencies/Contracts/','src/NuGet/Microsoft.CodeAnalysis.BuildClient.Package/')
removed=[]
with tarfile.open(archive) as t:
    for member in t:
        rel=member.name.partition('/')[2]
        if not member.isfile() or not (rel.startswith(selected) or rel in {'License.txt','ThirdPartyNotices.rtf'}):continue
        if Path(rel).suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.lib','.obj','.resources'}:removed.append(rel);continue
        path=roslyn/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(t.extractfile(member).read())
run('prepare-task-plan',[sys.executable,'-X','utf8',here/'prepare-task-plan.py',roslyn,root/'task-plan'])
run('evaluate-task',[host,tool/'bin/Release/net8.0/EvaluateProjects.dll',root/'task-plan/wrappers.json',root/'task-plan/evaluated.json'])
(root/'prepare-results.json').write_text(json.dumps(dict(commands=commands,msbuild_original_compile_items=1195,removed_roslyn_binary_fixtures=removed,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS cold source MSBuild17 NET8 and Roslyn NET10 task preparation')
