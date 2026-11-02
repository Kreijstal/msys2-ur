"""Fresh source-feed consumer: real Workspaces/Channels behavior and full API/resources."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

resume='--resume' in sys.argv[1:]
args=[p for p in sys.argv[1:] if p!='--resume']
root,out,check=(Path(p).resolve() for p in args[:3])
installed=len(args)==4
selected_feed=Path(args[3]).resolve() if installed else out/'feed'
assert resume or not check.exists(),check
check.mkdir(parents=True,exist_ok=resume)
here=Path(__file__).resolve().parent
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(path):
    path=Path(path).resolve()
    if path.is_relative_to(root):return native_root+'/'+path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
def posix(path):
    path=path.replace('\\','/')
    if path.lower().startswith(native_root.lower()+'/'):return root/path[len(native_root)+1:]
    return Path(subprocess.check_output(['cygpath','-u',path],text=True).strip())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((out/'source-inputs.json').read_text())
roslyn=out/'roslyn-source'
settings=E.parse(roslyn/'eng/targets/Settings.props')
def key(value):
    if not value:value=settings.findtext('.//MicrosoftSharedPublicKey')
    while value.startswith('$('):value=settings.findtext('.//'+value[2:-1])
    return value
expected={}
for name,record in source['projects'].items():
    source_root=roslyn
    for path,digest in {**record['original_cs'],**record['original_resources']}.items():assert sha(source_root/path)==digest,(name,path)
    original=E.parse(roslyn/record['original_project']);friends=[]
    for kind in ['InternalsVisibleTo','RestrictedInternalsVisibleTo']:
        for item in original.iter(kind):
            friends.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item.get('Include')+', PublicKey='+key(item.get('Key','')))+')]')
            if kind=='RestrictedInternalsVisibleTo':
                ns=item.get('Namespace') or 'Microsoft.CodeAnalysis.ExternalAccess.'+item.get('Partner')+'.Api'
                friends.append('[assembly: System.Runtime.CompilerServices.RestrictedInternalsVisibleTo('+json.dumps(item.get('Include'))+', '+json.dumps(ns)+')]')
    expected[name]=dict(friend_attributes=list(dict.fromkeys(friends)))
    suffix='common' if name=='Microsoft.CodeAnalysis.Workspaces' else 'csharp'
    folder=(roslyn/record['original_project']).parent
    (check/('api-'+suffix+'.txt')).write_text((folder/'PublicAPI.Shipped.txt').read_text().rstrip()+'\n'+(folder/'PublicAPI.Unshipped.txt').read_text().rstrip()+'\n')
(check/'source-items.json').write_text(json.dumps(expected,indent=2)+'\n')
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for i,feed in enumerate([selected_feed,Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(sources,'add',key='source'+str(i),value=native(feed))
E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
standard=check/'standard-consumer';standard.mkdir(exist_ok=resume)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='netstandard2.0',AssemblyName='StandardWorkspaceConsumer',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/StandardConsumer.cs'))
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.14.0]')
E.ElementTree(tree).write(standard/'Build.csproj',encoding='utf-8',xml_declaration=True)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='Check',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',
                EnableNETAnalyzers='false',NuGetAudit='false',LangVersion='preview',Nullable='disable',
                CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
for name in ['Check.cs','CheckApi.cs','ChannelChecks.cs']:E.SubElement(items,'Compile',Include=native(here/'inputs'/name))
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.14.0]')
E.SubElement(items,'ProjectReference',Include='standard-consumer/Build.csproj')
E.ElementTree(tree).write(check/'Check.csproj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
with (check/'build.log').open('w') as log:
    subprocess.run([dotnet,'build',native(check/'Check.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
feeds=[selected_feed,Path('/clang64/lib/dotnet/library-packs')]
feed_packages={}
for feed in feeds:
    for p in feed.glob('*.nupkg'):feed_packages.setdefault(p.name.lower(),p)
assets=json.loads((check/'obj/project.assets.json').read_text());binary=check/'bin/Release/net8.0';packages={}
standard_assets=json.loads((standard/'obj/project.assets.json').read_text())
standard_target=next(iter(standard_assets['targets'].values()))
for ident in ['Microsoft.CodeAnalysis.Workspaces.Common','Microsoft.CodeAnalysis.CSharp.Workspaces']:
    name='Microsoft.CodeAnalysis.Workspaces' if ident.endswith('.Common') else ident
    assert set(standard_target[ident+'/4.14.0']['compile'])=={'lib/netstandard2.0/'+name+'.dll'}
target=next(iter(assets['targets'].values()))
runtime_target=next(iter(json.loads((binary/'Check.deps.json').read_text())['targets'].values()))
for library,entry in assets['libraries'].items():
    if entry['type']!='package':continue
    ident,version=library.split('/');name=ident.lower()+'.'+version+'.nupkg';assert name in feed_packages,library
    archive=feed_packages[name];cache=check/'cache'/entry['path']
    assert (cache/name).read_bytes()==archive.read_bytes(),library
    with zipfile.ZipFile(archive) as z:
        for path in z.namelist():
            if path.endswith('.dll'):assert (cache/path).read_bytes()==z.read(path),(library,'cache',path)
        selected={path for kind in ['runtime','resources'] for path in runtime_target.get(library,{}).get(kind,{}) if path.endswith('.dll')}
        for path in selected:
            parts=path.split('/');assert parts[0]=='lib' and parts[1] in ['netstandard2.0','netstandard2.1','net8.0'],(library,path)
            wanted='net8.0' if ident=='Humanizer.Core' or ident.startswith('System.Composition.') else 'netstandard2.1' if ident=='Microsoft.Bcl.AsyncInterfaces' else 'netstandard2.0'
            assert parts[1]==wanted,(library,path,wanted)
            assert (binary/'/'.join(parts[2:])).read_bytes()==z.read(path),(library,'selected asset',path)
    packages[library]=sha(archive)
refs=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'],text=True).strip()
command=[dotnet,native(binary/'Check.dll'),native(out/'localization.json'),native(check/'source-items.json'),refs,native(check)]
with (check/'run.log').open('w') as log:
    result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
(check/'run.exit').write_text(str(result.returncode)+'\n')
assert result.returncode==0,(result.returncode,check/'run.log')
(check/'results.json').write_text(json.dumps(dict(command=command,exit_code=0,source_package_sha256=packages,
    all_fresh_cache_archives_and_netstandard_managed_assets_match=True,source_production_cs_changes=0,
    separately_compiled_standard20_consumer_passed=True,formal_pacman_installed=installed,full_original_generator_bundle_complete=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS fresh source Workspaces4.14: complete APIs/friends/resources, MEF/refactoring/code actions and real source Channels9 behavior')
