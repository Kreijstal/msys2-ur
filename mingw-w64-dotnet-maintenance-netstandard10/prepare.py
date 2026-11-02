"""Prepare exact maintenance-package netstandard2.0 sources for Roslyn source-build."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

root,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins=json.loads((here/'inputs/publisher-source-pins.json').read_text())
archives={
 '6b84308c9ad012f53240d72c1d716d7e42546483':('maintenance-6b84308c.tar.gz','5f8a5d6a7fe51c06216d21eb06fd2c4ad4bae2b4a3b13319a74d790919b7492c'),
 'f62ca0009b038cab4725a720f386623a969d73ad':('maintenance-f62ca000.tar.gz','76d2a3bcca49a0463e8bdf4dd79c0772bc899d7427b3d4ade0120036e48df5eb')}
sources={};removed=[]
for commit,(filename,digest) in archives.items():
    archive=root/filename
    assert sha(archive)==digest
    with tarfile.open(archive) as tar:
        assert tar.pax_headers['comment']==commit
        tar.extractall(out,filter='data')
    source=out/('maintenance-packages-'+commit);sources[commit]=source
    for p in source.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources'}:
            removed.append(dict(commit=commit,path=p.relative_to(source).as_posix(),sha256=sha(p)));p.unlink()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
def posix(value):
    value=value.replace('\\','/');assert value.lower().startswith(native_root.lower()+'/'),value
    return root/value[len(native_root)+1:]
def save(tree,path):
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
order=['System.Runtime.CompilerServices.Unsafe','System.Buffers','System.Numerics.Vectors','System.Memory','System.Threading.Tasks.Extensions']
wrappers={}
for name in order[1:]:
    source=sources[pins[name]['commit']];original=source/'src'/name/'src'/(name+'.csproj')
    folder=out/'evaluation'/name;folder.mkdir(parents=True)
    tree=E.parse(original).getroot();tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile','ProjectReference','EmbeddedResource'}:continue
        for attr in ['Include','Remove','Update']:
            value=item.get(attr,'').replace('\\','/')
            if value and '$(' not in value:item.set(attr,native(original.parent/value))
    save(tree,folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',
                    CommonPath=native(source/'src/Common')+'/',NetFrameworkMinimum='net462',NetMinimum='net6.0').items():E.SubElement(pg,k).text=v
    ig=E.SubElement(wrapper,'ItemGroup')
    E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/**/*.net.cs;'+native(original.parent)+'/**/*.netframework.cs')
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    path=folder/(name+'.csproj');save(wrapper,path);wrappers[name]=native(path)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
dotnet='/clang64/lib/dotnet/dotnet.exe'
tool=out/'evaluate-tool/bin/Release/net8.0/EvaluateReferenceProjects.dll'
sdk=Path('/clang64/lib/dotnet/sdk/8.0.131')
env=dict(os.environ,MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'),MSBuildEnableWorkloadResolver='false')
helper=out/'evaluate-tool';helper.mkdir()
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='EvaluateReferenceProjects',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(project,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/EvaluateProjects.cs'))
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
 E.SubElement(E.SubElement(items,'Reference',Include=name),'HintPath').text=native(sdk/(name+'.dll'))
save(project,helper/'Build.csproj');(helper/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env.update(DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
with (helper/'build.log').open('w') as log:
 subprocess.run([dotnet,'build',native(helper/'Build.csproj'),'-c','Release','--configfile',native(helper/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (out/'evaluation.log').open('w') as log:
    subprocess.run([dotnet,native(tool),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for name in ['Microsoft','Open']:(out/(name+'.pubkey')).write_bytes(bytes.fromhex((here/'inputs'/(name+'.pubkey.hex')).read_text()))
def package_metadata(tree,name):
    pg=E.SubElement(tree,'PropertyGroup');pin=pins[name]
    for k,v in dict(Version=pin['version'],FileVersion=pin['version']+'.0',InformationalVersion=pin['version']+'+'+pin['commit'],IncludeSourceRevisionInInformationalVersion='false',PackageId=name,RepositoryUrl='https://github.com/dotnet/maintenance-packages',RepositoryCommit=pin['commit'],PackageLicenseExpression='MIT').items():E.SubElement(pg,k).text=v
records={};resources=[]
for name in order:
    folder=out/name;folder.mkdir()
    source=sources[pins[name]['commit']];original=source/'src'/name/'src'/(name+('.ilproj' if name==order[0] else '.csproj'))
    if name==order[0]:
        versioning=source/'src'/name/'Versioning.props'
        selected=[original.parent/(name+'.il')]
        records[name]=dict(configuration='Release',original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),commit=pins[name]['commit'],version=pins[name]['version'],assembly_version='6.0.0.0',key='Microsoft',original_sources={p.relative_to(source).as_posix():sha(p) for p in selected},original_extra_inputs={versioning.relative_to(source).as_posix():sha(versioning)},dependencies={},production_source_changes=0)
        continue
    selected=[posix(item['full_path']) for item in evaluated[name]['items']['Compile']]
    resource=original.parent/'Resources/Strings.resx'
    if resource.is_file():selected.append(source/'src/Common/src/System/SR.cs')
    assert len(selected)==len(set(selected)) and all(p.is_file() for p in selected),name
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    assert 'DEBUG' not in evaluated[name]['properties']['DefineConstants'].split(';'),name
    key=evaluated[name]['properties']['StrongNameKeyId'];assert key in ['Open','Microsoft'],key
    for k,v in dict(TargetFramework='netstandard2.0',AssemblyName=name,AssemblyVersion=evaluated[name]['properties']['AssemblyVersion'],EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',
                    AllowUnsafeBlocks='true',Nullable='disable',LangVersion='preview',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',
                    CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='../'+key+'.pubkey',
                    DefineConstants=evaluated[name]['properties']['DefineConstants'],GenerateAssemblyConfigurationAttribute='false',GenerateNeutralResourcesLanguageAttribute='false').items():E.SubElement(pg,k).text=v
    package_metadata(tree,name)
    ig=E.SubElement(tree,'ItemGroup')
    for p in selected:E.SubElement(ig,'Compile',Include=native(p))
    deps=pins[name]['dependencies']
    actual={Path(i['full_path'].replace('\\','/')).stem for i in evaluated[name]['items']['ProjectReference']}
    assert actual==set(deps),(name,actual,deps)
    for dep,version in deps.items():E.SubElement(ig,'PackageReference',Include=dep,Version='['+version+']')
    for typ,value,literal in [('System.CLSCompliantAttribute','true',True),('System.Reflection.AssemblyDefaultAliasAttribute',name,False),('System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute','System.Runtime.InteropServices.DllImportSearchPath.AssemblyDirectory | System.Runtime.InteropServices.DllImportSearchPath.System32',True)]:
        a=E.SubElement(ig,'AssemblyAttribute',Include=typ);E.SubElement(a,'_Parameter1').text=value
        if literal:E.SubElement(a,'_Parameter1_IsLiteral').text='true'
    for meta in ['PreferInbox','Serviceable']:E.SubElement(ig,'AssemblyMetadata',Include=meta,Value='True')
    if resource.is_file():
        logical='FxResources.'+name+'.SR'
        code=['namespace FxResources.'+name+' { internal static class SR {} }','namespace System { internal static partial class SR {','internal static global::System.Resources.ResourceManager ResourceManager {get;} = new global::System.Resources.ResourceManager("'+logical+'",typeof(FxResources.'+name+'.SR).Assembly);']
        strings={}
        for e in E.parse(resource).iter('data'):
            keyname=e.get('name');assert keyname.isidentifier();strings[keyname]=e.findtext('value') or ''
            code.append('internal static string @'+keyname+' => GetResourceString("'+keyname+'");')
        code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
        E.SubElement(ig,'Compile',Include='SR.Generated.cs');E.SubElement(ig,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
        a=E.SubElement(ig,'AssemblyAttribute',Include='System.Resources.NeutralResourcesLanguageAttribute');E.SubElement(a,'_Parameter1').text='en-US'
        resources.append(dict(assembly=name,logical_name=logical,strings=strings))
    for file in [source/'LICENSE',source/'LICENSE.TXT',source/'THIRD-PARTY-NOTICES.TXT',original.parent/'PACKAGE.md',original.parent/(name+'.xml')]:
        if file.is_file():E.SubElement(ig,'None',Include=native(file),Pack='true',PackagePath='' if file.suffix!='.xml' else 'lib/netstandard2.0')
    capture=E.SubElement(tree,'Target',Name='CaptureCompilerInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath']:
        E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree,folder/'Build.csproj')
    extras={p.relative_to(source).as_posix():sha(p) for p in [resource] if p.is_file()}
    records[name]=dict(configuration='Release',original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),commit=pins[name]['commit'],version=pins[name]['version'],assembly_version=evaluated[name]['properties']['AssemblyVersion'],key=key,original_sources={p.relative_to(source).as_posix():sha(p) for p in selected},original_extra_inputs=extras,dependencies=deps,production_source_changes=0)
(out/'feed').mkdir()
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for name,path in [('private',out/'feed'),('installed-source',Path('/clang64/lib/dotnet/library-packs'))]:E.SubElement(feeds,'add',key=name,value=native(path))
save(config,out/'NuGet.config')
(out/'source-inputs.json').write_text(json.dumps(dict(archives=archives,projects=records,order=order),indent=2)+'\n')
(out/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
print('Prepared exact source maintenance dependencies', {n:len(r['original_sources']) for n,r in records.items()})

(out/'tool-inputs.json').write_text(json.dumps({str(p):dict(owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip(),sha256=sha(p)) for p in [Path('/clang64/bin/ilasm10.exe'),Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll'),Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0/netstandard.dll')]},indent=2)+'\n')
