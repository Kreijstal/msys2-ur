"""Fresh source-only consumers, isolated source execution and original API contracts."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

resume='--resume' in sys.argv[1:]
root,out,check=(Path(p).resolve() for p in sys.argv[1:] if p!='--resume')
assert resume or not check.exists(),check
check.mkdir(parents=True,exist_ok=resume)
here=Path(__file__).resolve().parent
source=root/'roslyn-deps9-1/runtime-source';libs=source/'src/libraries'
record=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
def posix(p):
    p=p.replace('\\','/');assert p.lower().startswith(native_root.lower()+'/'),p
    return root/p[len(native_root)+1:]
def save(tree,path):
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def config(path,feeds):
    tree=E.Element('configuration');items=E.SubElement(tree,'packageSources');E.SubElement(items,'clear')
    for i,feed in enumerate(feeds):E.SubElement(items,'add',key='source'+str(i),value=native(feed))
    save(tree,path)
library_feeds=[out/'feed',root/'maintenance20-1/feed',root/'netstandard20-2/feed',Path('/clang64/lib/dotnet/library-packs')]
tool_feeds=[root/'roslyn414-1/feed',root/'roslyn-deps9-1/feed',Path('/clang64/lib/dotnet/library-packs')]
config(check/'NuGet.config',library_feeds);config(check/'Tools.NuGet.config',tool_feeds)
def project(path,properties,files,packages):
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseAppHost='false',UseSharedCompilation='false',AllowUnsafeBlocks='true',LangVersion='preview',**properties).items():E.SubElement(pg,k).text=v
    items=E.SubElement(tree,'ItemGroup')
    for file in files:E.SubElement(items,'Compile',Include=native(file))
    for name,version in packages.items():E.SubElement(items,'PackageReference',Include=name,Version='['+version+']')
    save(tree,path)
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command,log,extra=None):
    with log.open('w') as stream:r=subprocess.run(command,env=dict(env,**(extra or {})),stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,(command,log)
library=check/'library';library.mkdir(exist_ok=resume)
project(library/'Build.csproj',dict(TargetFramework='netstandard2.0',AssemblyName='Runtime9Consumer',CopyLocalLockFileAssemblies='true'),[here/'inputs/Consumer.cs'],{**{n:'9.0.0' for n in record['order']},'System.Composition':'9.0.0'})
run([dotnet,'build',native(library/'Build.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],check/'library-build.log')
binary=library/'bin/Release/netstandard2.0'
maintenance=list(json.loads((root/'maintenance20-1/source-inputs.json').read_text())['projects'])
assert all((binary/(n+'.dll')).is_file() for n in record['order']+maintenance)
baseline_projects={};baseline_inputs={}
for name in record['order']:
    original=libs/name/'ref'/(name+'.csproj')
    if not original.is_file():continue
    folder=check/'api-evaluation'/name;folder.mkdir(parents=True,exist_ok=resume)
    body=E.parse(original).getroot();body.attrib.pop('Sdk')
    for item in body.iter():
        if item.tag not in {'Compile','ProjectReference'}:continue
        value=item.get('Include','').replace('\\','/')
        if value and '$(' not in value:item.set('Include',native(original.parent/value))
    save(body,folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',Nullable='enable',EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',NetCoreAppCurrent='net9.0',NetCoreAppPrevious='net8.0',NetCoreAppMinimum='net8.0',NetFrameworkMinimum='net462',CommonPath=native(libs/'Common/src')+'/',LibrariesProjectRoot=native(libs)+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/').items():E.SubElement(pg,k).text=v
    E.SubElement(wrapper,'Import',Project='upstream.proj');E.SubElement(wrapper,'Import',Project=native(out/'original-shared-sources.targets'))
    path=folder/(name+'.csproj');save(wrapper,path);baseline_projects[name]=native(path)
    baseline_inputs[original.relative_to(source).as_posix()]=sha(original)
(check/'api-wrappers.json').write_text(json.dumps(baseline_projects,indent=2)+'\n')
run([dotnet,native(root/'roslyn414-1/evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'),native(check/'api-wrappers.json'),native(check/'api-evaluated.json')],check/'api-evaluation.log',dict(MSBuildSDKsPath=native(Path('/clang64/lib/dotnet/sdk/8.0.131/Sdks')),MSBUILD_EXE_PATH=native(Path('/clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll'))))
evaluated=json.loads((check/'api-evaluated.json').read_text());baselines={}
for name,item in evaluated.items():
    files=[posix(i['full_path']) for i in item['items']['Compile']]
    assert files and all(p.is_file() for p in files)
    for file in files:baseline_inputs[file.relative_to(source).as_posix()]=sha(file)
    baselines[name]=dict(sources=[native(p) for p in files],defines=item['properties']['DefineConstants'].split(';'))
name='Microsoft.Bcl.AsyncInterfaces'
baselines[name]=dict(sources=[native(source/p) for p in record['projects'][name]['original_cs']],defines=['NETSTANDARD','NETSTANDARD2_0','NETSTANDARD2_0_OR_GREATER'])
for name in record['order']:
    if name.startswith('System.Composition.'):
        dll=root/'roslyn-deps9-1'/name/'bin/Release/net8.0'/(name+'.dll');assert dll.is_file()
        with zipfile.ZipFile(root/'roslyn-deps9-1/feed'/(name+'.9.0.0.nupkg')) as z:assert dll.read_bytes()==z.read('lib/net8.0/'+name+'.dll')
        baselines[name]=dict(metadata=native(dll),source_net8_baseline_sha256=sha(dll))
assert set(baselines)==set(record['order'])
(check/'api-source-inputs.json').write_text(json.dumps(baseline_inputs,indent=2)+'\n')
settings=dict(maintenance_names=maintenance,codepages_data_sha256=sha(libs/'System.Text.Encoding.CodePages/src/Data/codepages.nlp'),
              standard_reference_paths=[native(p) for p in sorted((root/'netstandard20-2/ref').glob('*.dll'))],
              net8_baseline_reference_paths=[native(p) for p in sorted(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll'))]+[native(root/'roslyn-deps9-1'/n/'bin/Release/net8.0'/(n+'.dll')) for n in record['order'] if n.startswith('System.Composition.')],api_baselines=baselines)
(check/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
runner=check/'runner';runner.mkdir(exist_ok=resume)
project(runner/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckRuntime9Netstandard',Nullable='enable'),[here/'inputs/Check.cs',here/'inputs/CheckApi.cs'],{'Microsoft.CodeAnalysis.CSharp':'4.14.0'})
run([dotnet,'build',native(runner/'Build.csproj'),'-c','Release','--configfile',native(check/'Tools.NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],check/'runner-build.log',dict(NUGET_PACKAGES=native(check/'tool-cache')))
run([dotnet,native(runner/'bin/Release/net8.0/CheckRuntime9Netstandard.dll'),native(root),native(out),native(binary),native(check/'settings.json'),native(check/'runtime-results.json')],check/'run.log')
result=dict(runtime=json.loads((check/'runtime-results.json').read_text()),fresh_consumer_exit_code=0,all_original_api_baselines_selected=True,source_netstandard20_consumer_packages=list(json.loads((library/'obj/project.assets.json').read_text())['libraries']),formal_pacman_installed=False,full_dependency_goal_complete=False)
(check/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS eleven original netstandard2.0 implementations, exact isolated runtime/native/resource checks and original API gates')
