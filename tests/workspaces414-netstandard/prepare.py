"""Prepare complete original Workspaces4.14 netstandard2.0 source projects."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

root,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
source=root/'roslyn414-1/roslyn-source';baseline=root/'workspaces414-1'
old=json.loads((baseline/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert old['roslyn_commit']=='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b'
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
names=['Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces'];wrappers={}
for name in names:
    original=source/old['projects'][name]['original_project'];folder=out/'evaluation'/name;folder.mkdir(parents=True)
    for path,digest in old['projects'][name]['original_cs'].items():assert sha(source/path)==digest,path
    body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
    tree=E.fromstring(body);tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile','Import','ProjectReference','EmbeddedResource'}:continue
        for attr in ['Include','Remove','Update','Project']:
            value=item.get(attr,'').replace('\\','/')
            if value and '$(' not in value and not value.startswith('/') and not(len(value)>1 and value[1]==':'):item.set(attr,native(original.parent/value))
    save(tree,folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',NetRoslynSourceBuild='net8.0;net9.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',DotNetBuildSourceOnly='true',DefineConstants='$(DefineConstants);DOTNET_BUILD_FROM_SOURCE').items():E.SubElement(pg,k).text=v
    E.SubElement(wrapper,'Import',Project=native(source/'eng/Versions.props'));E.SubElement(wrapper,'Import',Project=native(source/'eng/Directory.Packages.props'))
    items=E.SubElement(wrapper,'ItemGroup')
    for p in sorted(original.parent.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(p))
    for p in sorted(original.parent.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(p))
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    path=folder/(name+'.csproj');save(wrapper,path);wrappers[name]=native(path)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
env=dict(os.environ,MSBuildSDKsPath=native(Path('/clang64/lib/dotnet/sdk/8.0.131/Sdks')),MSBUILD_EXE_PATH=native(Path('/clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll')),MSBuildEnableWorkloadResolver='false')
with (out/'evaluation.log').open('w') as log:
    subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(root/'roslyn414-1/evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for item in evaluated.values():assert 'DEBUG' not in item['properties']['DefineConstants'].split(';'),item['properties']['DefineConstants']
shutil.copyfile(baseline/'MicrosoftShared.pubkey',out/'MicrosoftShared.pubkey')
props={}
for group in E.parse(source/'eng/Versions.props').getroot().findall('PropertyGroup'):
    if "'$(DotNetBuildSourceOnly)' != 'true'" in group.get('Condition',''):continue
    for e in group:
        if e.text and '$(' not in e.text:props[e.tag]=e.text.strip()
versions={}
central=E.parse(source/'eng/Directory.Packages.props')
for group in central.getroot().findall('PropertyGroup'):
    for e in group:
        if e.text and '$(' not in e.text:props[e.tag]=e.text.strip()
for item in central.iter('PackageVersion'):
    v=item.get('Version','')
    if v.startswith('$(') and v.endswith(')'):v=props.get(v[2:-1],'')
    if v:versions[item.get('Include')]=v
records={}
project_ids={'Microsoft.CodeAnalysis':'Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.CSharp':'Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces':'Microsoft.CodeAnalysis.Workspaces.Common'}
for name in names:
    folder=out/name;folder.mkdir();tree=E.parse(baseline/name/'Build.csproj')
    tree.find('.//TargetFramework').text='netstandard2.0';tree.find('.//DefineConstants').text=evaluated[name]['properties']['DefineConstants']
    items=tree.find('ItemGroup');assert items is not None
    for e in list(items):
        if e.tag=='PackageReference' or (e.tag=='Compile' and e.get('Include','').startswith(native(source))) or e.tag=='None':items.remove(e)
    selected=list(dict.fromkeys(posix(i['full_path']) for i in evaluated[name]['items']['Compile']))
    assert selected and all(p.is_file() for p in selected)
    assert not any('/Storage/SQLite/' in str(p) for p in selected)
    for p in selected:E.SubElement(items,'Compile',Include=native(p))
    minimums={};deps={}
    for item in evaluated[name]['items']['PackageReference']:
        ident=item['identity']
        if ident=='NETStandard.Library':continue
        assert ident in versions,(name,ident)
        minimums[ident]=versions[ident];deps[ident]='9.0.0' if ident=='System.Threading.Channels' else versions[ident]
    for item in evaluated[name]['items']['ProjectReference']:
        ident=Path(item['full_path'].replace('\\','/')).stem;assert ident in project_ids,(name,ident)
        deps[project_ids[ident]]='4.14.0'
    for ident,version in deps.items():E.SubElement(items,'PackageReference',Include=ident,Version='['+version+']',**({'PrivateAssets':'compile'} if ident=='Humanizer.Core' else {}))
    for p in (baseline/name).iterdir():
        if p.is_file() and p.suffix in {'.cs','.resx'}:shutil.copyfile(p,folder/p.name)
    for file in ['License.txt','THIRD-PARTY-NOTICES.txt']:E.SubElement(items,'None',Include=native(source/file),Pack='true',PackagePath='')
    target=E.SubElement(tree.getroot(),'Target',Name='CaptureOriginalShippingInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree.getroot(),folder/'Build.csproj')
    records[name]=dict(original_project=old['projects'][name]['original_project'],original_project_sha256=old['projects'][name]['original_project_sha256'],original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},original_resources=old['projects'][name]['original_resources'],original_package_minimums=minimums,resolved_dependencies=deps,production_cs_changes=0,framework='netstandard2.0',original_sqlite_source_build_exclusion=True)
resources=[r for r in json.loads((baseline/'localization.json').read_text()) if r['assembly'] in names]
(out/'localization.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
platforms=out/'platform-feed';platforms.mkdir();shutil.copyfile('/clang64/lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.2.nupkg',platforms/'microsoft.netcore.platforms.1.1.2.nupkg')
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for i,path in enumerate([out/'feed',root/'roslyn414-ns20-3/feed',root/'runtime9-ns20-2/feed',root/'humanizer-ns20-1/feed',root/'maintenance20-1/feed',root/'netstandard20-2/feed',platforms]):E.SubElement(feeds,'add',key='source'+str(i),value=native(path))
save(config,out/'NuGet.config');(out/'feed').mkdir()
(out/'source-inputs.json').write_text(json.dumps(dict(roslyn_version='4.14.0',roslyn_commit=old['roslyn_commit'],projects=records,original_versions_sha256=sha(source/'eng/Versions.props'),original_central_packages_sha256=sha(source/'eng/Directory.Packages.props'),full_dependency_goal_complete=False),indent=2)+'\n')
print('Prepared original Workspaces netstandard2.0 source projects', {n:len(r['original_cs']) for n,r in records.items()}, {n:r['resolved_dependencies'] for n,r in records.items()})
