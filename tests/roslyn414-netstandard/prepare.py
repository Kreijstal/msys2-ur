"""Select original Roslyn4.14 netstandard2.0 projects with source-only dependencies."""
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
here=Path(__file__).resolve().parent
previous=root/'roslyn414-1';source=previous/'roslyn-source'
old=json.loads((previous/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert old['roslyn_commit']=='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b'
assert sha(root/'roslyn-4.14.0-8edf7bcd.tar.gz')==old['source_archive_sha256']=='8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c'
for item in old['projects'].values():
    for path,digest in item['original_cs'].items():assert sha(source/path)==digest,path
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
shutil.copyfile(previous/'Roslyn.public.snk',out/'Roslyn.public.snk')
wrappers={}
for name,language in [('Microsoft.CodeAnalysis','Core'),('Microsoft.CodeAnalysis.CSharp','CSharp')]:
    main=source/'src/Compilers'/language/'Portable';original=main/(name+'.csproj')
    folder=out/'evaluation'/name;folder.mkdir(parents=True)
    body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(main)+'/')
    tree=E.fromstring(body);tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile','Import','ProjectReference','EmbeddedResource'}:continue
        for attr in ['Include','Remove','Update','Project']:
            value=item.get(attr,'').replace('\\','/')
            if value and '$(' not in value and not value.startswith('/') and not(len(value)>1 and value[1]==':'):item.set(attr,native(main/value))
    save(tree,folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',NetRoslynSourceBuild='net8.0;net9.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',DotNetBuildSourceOnly='true',RootNamespace=name,DefineConstants='$(DefineConstants);DOTNET_BUILD_FROM_SOURCE',CompilerGeneratedFilesOutputPath=native(main/'Generated')).items():E.SubElement(pg,k).text=v
    E.SubElement(wrapper,'Import',Project=native(source/'eng/Versions.props'))
    E.SubElement(wrapper,'Import',Project=native(source/'eng/Directory.Packages.props'))
    items=E.SubElement(wrapper,'ItemGroup')
    for p in sorted(main.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(p))
    for p in sorted(main.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(p))
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    path=folder/(name+'.csproj');save(wrapper,path);wrappers[name]=native(path)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
env=dict(os.environ,MSBuildSDKsPath=native(Path('/clang64/lib/dotnet/sdk/8.0.131/Sdks')),MSBUILD_EXE_PATH=native(Path('/clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll')),MSBuildEnableWorkloadResolver='false')
with (out/'evaluation.log').open('w') as log:
    subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(previous/'evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for item in evaluated.values():assert 'DEBUG' not in item['properties']['DefineConstants'].split(';'),item['properties']['DefineConstants']
central=E.parse(source/'eng/Versions.props')
properties={}
for group in central.getroot().findall('PropertyGroup'):
    condition=group.get('Condition','')
    if "'$(DotNetBuildSourceOnly)' != 'true'" in condition:continue
    for item in group:
        if item.text and '$(' not in item.text:properties[item.tag]=item.text.strip()
package_versions={}
for item in E.parse(source/'eng/Directory.Packages.props').iter('PackageVersion'):
    version=item.get('Version','')
    if version.startswith('$(') and version.endswith(')'):version=properties.get(version[2:-1],'')
    if version:package_versions[item.get('Include')]=version
records={}
for name,language in [('Microsoft.CodeAnalysis','Core'),('Microsoft.CodeAnalysis.CSharp','CSharp')]:
    folder=out/name;folder.mkdir()
    baseline=previous/name;tree=E.parse(baseline/'Build.csproj');pg=tree.find('PropertyGroup')
    assert pg is not None
    pg.find('TargetFramework').text='netstandard2.0'
    tree.find('.//DefineConstants').text=evaluated[name]['properties']['DefineConstants']
    selected=[posix(i['full_path']) for i in evaluated[name]['items']['Compile']]
    if language=='CSharp':selected=[p for p in selected if not p.is_relative_to(source/'src/Compilers/CSharp/Portable/Generated')]
    selected=list(dict.fromkeys(selected));assert all(p.is_file() for p in selected)
    groups=tree.findall('ItemGroup');items=groups[0]
    for item in list(items):
        if item.tag=='PackageReference' or (item.tag=='Compile' and item.get('Include') not in {'Friends.Generated.cs'} and not item.get('Include','').endswith('.Generated.cs')):
            items.remove(item)
        elif item.tag=='Compile' and item.get('Include','').startswith(native(source)):
            items.remove(item)
    # Remove only the old original source paths; preserve generated resource wrappers.
    for item in list(items):
        if item.tag=='Compile' and (item.get('Include','').startswith(native(source)) or '/generated/' in item.get('Include','')):items.remove(item)
    for path in selected:E.SubElement(items,'Compile',Include=native(path))
    if language=='CSharp':E.SubElement(items,'Compile',Include=native(previous/'generated')+'/*.cs')
    dependencies={};minimums={}
    for item in evaluated[name]['items']['PackageReference']:
        ident=item['identity']
        if ident=='NETStandard.Library':continue
        assert ident in package_versions,(name,ident)
        minimums[ident]=package_versions[ident]
        dependencies[ident]='9.0.0' if ident=='System.Text.Encoding.CodePages' else package_versions[ident]
    if language=='CSharp':dependencies['Microsoft.CodeAnalysis.Common']='4.14.0'
    for ident,version in dependencies.items():E.SubElement(items,'PackageReference',Include=ident,Version='['+version+']')
    for file in baseline.glob('*.cs'):shutil.copyfile(file,folder/file.name)
    for file in baseline.glob('*.resx'):shutil.copyfile(file,folder/file.name)
    for file in [source/'License.txt',source/'THIRD-PARTY-NOTICES.txt']:
        if file.is_file():E.SubElement(items,'None',Include=native(file),Pack='true',PackagePath='')
    capture=E.SubElement(tree.getroot(),'Target',Name='CaptureActualCompilerInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:
        E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree.getroot(),folder/'Build.csproj')
    records[name]=dict(original_project=old['projects'][name]['original_project'],original_project_sha256=old['projects'][name]['original_project_sha256'],original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},original_resources=old['projects'][name]['original_resources'],original_package_minimums=minimums,resolved_dependencies=dependencies,production_cs_changes=0,framework='netstandard2.0',friend_declarations=old['projects'][name]['friend_declarations'])
shutil.copyfile(previous/'localization.json',out/'localization.json')
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for name,path in [('private',out/'feed'),('runtime9',root/'runtime9-ns20-2/feed'),('maintenance',root/'maintenance20-1/feed'),('standard',root/'netstandard20-2/feed'),('installed-source',Path('/clang64/lib/dotnet/library-packs'))]:E.SubElement(feeds,'add',key=name,value=native(path))
save(config,out/'NuGet.config');(out/'feed').mkdir()
(out/'source-inputs.json').write_text(json.dumps(dict(roslyn_version='4.14.0',roslyn_commit=old['roslyn_commit'],source_archive_sha256=old['source_archive_sha256'],source_root=native(source),projects=records,
    original_versions_sha256=sha(source/'eng/Versions.props'),original_central_packages_sha256=sha(source/'eng/Directory.Packages.props'),original_generated_sources=json.loads((previous/'generated-sources.json').read_text()),full_dependency_goal_complete=False),indent=2)+'\n')
print('Prepared original Roslyn4.14 netstandard2.0 projects', {n:len(r['original_cs']) for n,r in records.items()}, {n:r['resolved_dependencies'] for n,r in records.items()},flush=True)
