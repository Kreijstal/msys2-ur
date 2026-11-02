"""Prepare complete original Workspaces4.14 and source9 Channels dependency."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root, out = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
roslyn=out/'roslyn-source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(path):
    path=Path(path).resolve()
    if path.is_relative_to(root):return native_root+'/'+path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
def posix(path):
    path=path.replace('\\','/');assert path.lower().startswith(native_root.lower()+'/')
    return root/path[len(native_root)+1:]
def save(tree,path):
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
subprocess.run(['/clang64/bin/python.exe',native(here/'extract-source.py'),native(root/'roslyn-4.14.0-8edf7bcd.tar.gz'),native(out)],check=True)
names={
 'Microsoft.CodeAnalysis.Workspaces':roslyn/'src/Workspaces/Core/Portable/Microsoft.CodeAnalysis.Workspaces.csproj',
 'Microsoft.CodeAnalysis.CSharp.Workspaces':roslyn/'src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj'}
wrappers={}
for name,original in names.items():
    folder=out/'evaluation'/name;folder.mkdir(parents=True)
    body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
    tree=E.ElementTree(E.fromstring(body));tree.getroot().attrib.pop('Sdk')
    for item in tree.iter():
        for attribute in ['Include','Remove','Update','Project']:
            if item.tag not in {'Compile','Import','ProjectReference','EmbeddedResource'} or attribute not in item.attrib:continue
            value=item.get(attribute).replace('\\','/')
            if '$(' not in value and not value.startswith('/') and not (len(value)>1 and value[1]==':'):
                item.set(attribute,native(original.parent/value))
    save(tree.getroot(),folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    values=dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',
                EnableDefaultItems='false',DotNetBuildSourceOnly='true',NetRoslynSourceBuild='net8.0;net9.0',
                DefineConstants='$(DefineConstants);DOTNET_BUILD_FROM_SOURCE')
    for k,v in values.items():E.SubElement(pg,k).text=v
    E.SubElement(wrapper,'Import',Project=native(roslyn/'eng/Versions.props'))
    E.SubElement(wrapper,'Import',Project=native(roslyn/'eng/Directory.Packages.props'))
    items=E.SubElement(wrapper,'ItemGroup')
    for path in sorted(original.parent.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(path))
    for path in sorted(original.parent.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(path))
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    path=folder/(name+'.csproj');save(wrapper,path);wrappers[name]=native(path)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
sdk_native=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/sdk/8.0.131'],text=True).strip()
env=dict(os.environ,MSBuildSDKsPath=sdk_native+'/Sdks',MSBUILD_EXE_PATH=sdk_native+'/MSBuild.dll',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
helper=out/'evaluation-tool';helper.mkdir()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='EvaluateRoslynProjects',OutputType='Exe',EnableDefaultItems='false',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/EvaluateRoslynProjects.cs'))
for n in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    E.SubElement(E.SubElement(items,'Reference',Include=n),'HintPath').text=sdk_native+'/'+n+'.dll'
save(p,helper/'Build.csproj')
(helper/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env.update(DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
with (helper/'build.log').open('w') as log:subprocess.run([dotnet,'build',native(helper/'Build.csproj'),'-c','Release','--configfile',native(helper/'NuGet.config'),'-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
tool=helper/'bin/Release/net8.0/EvaluateRoslynProjects.dll'
with (out/'evaluation.log').open('w') as log:
    subprocess.run([dotnet,native(tool),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
settings=E.parse(roslyn/'eng/targets/Settings.props')
def public_key(value):
    if not value:value=settings.findtext('.//MicrosoftSharedPublicKey')
    while value.startswith('$(') and value.endswith(')'):
        value=settings.findtext('.//'+value[2:-1]);assert value
    assert all(c in '0123456789abcdefABCDEF' for c in value),value
    return value
localizations=[];records={}
def resource(items,folder,path,metadata,namespace,source_root):
    if path.suffix!='.resx':
        logical=metadata.get('LogicalName') or namespace+'.'+path.name
        E.SubElement(items,'EmbeddedResource',Include=native(path),LogicalName=logical);return
    classname=metadata.get('ClassName') or path.stem
    namespace=metadata.get('Namespace') or namespace
    if '.' in classname:namespace,_,classname=classname.rpartition('.')
    logical=(metadata.get('LogicalName') or metadata.get('ManifestResourceName') or namespace+'.'+path.stem).removesuffix('.resources')
    code=['#nullable enable','namespace '+namespace+' { internal static class '+classname+' {',
          'internal static global::System.Resources.ResourceManager ResourceManager { get; } = new global::System.Resources.ResourceManager('+json.dumps(logical)+', typeof('+classname+').Assembly);',
          'internal static global::System.Globalization.CultureInfo? Culture {get;set;}']
    for item in E.parse(path).iter('data'):
        key=item.get('name');assert key.isidentifier(),key
        code.append('internal static string @'+key+' => ResourceManager.GetString('+json.dumps(key)+', Culture)!;')
    code.append('}}');generated=folder/(namespace+'.'+classname+'.Generated.cs');generated.write_text('\n'.join(code)+'\n')
    E.SubElement(items,'Compile',Include=generated.name);E.SubElement(items,'EmbeddedResource',Include=native(path),LogicalName=logical+'.resources')
    localizations.append(dict(assembly=folder.name,resource=logical,culture='',strings={e.get('name'):e.findtext('value') or '' for e in E.parse(path).iter('data')}))
    ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
    for xlf_path in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
        xlf=E.parse(xlf_path);culture=xlf.find('x:file',ns).get('target-language')
        values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
        localized=E.parse(path)
        for e in localized.iter('data'):
            if e.get('name') in values:e.find('value').text=values[e.get('name')]
        target=folder/(logical+'.'+culture+'.resx');localized.write(target,encoding='utf-8',xml_declaration=True)
        E.SubElement(items,'EmbeddedResource',Include=target.name,LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
        localizations.append(dict(assembly=folder.name,resource=logical,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))

key=bytes.fromhex(public_key(''));assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'MicrosoftShared.pubkey').write_bytes(key)
for item in evaluated.values():assert 'DEBUG' not in item['properties']['DefineConstants'].split(';')
props={}
for group in E.parse(roslyn/'eng/Versions.props').getroot().findall('PropertyGroup'):
    if "'$(DotNetBuildSourceOnly)' != 'true'" in group.get('Condition',''):continue
    for item in group:
        if item.text and '$(' not in item.text:props[item.tag]=item.text.strip()
central=E.parse(roslyn/'eng/Directory.Packages.props')
for group in central.getroot().findall('PropertyGroup'):
    for item in group:
        if item.text and '$(' not in item.text:props[item.tag]=item.text.strip()
versions={}
for item in central.iter('PackageVersion'):
    value=item.get('Version','')
    if value.startswith('$(') and value.endswith(')'):value=props.get(value[2:-1],'')
    if value:versions[item.get('Include')]=value
maintenance={n:r['version'] for n,r in json.loads(Path('/clang64/share/doc/dotnet-maintenance-netstandard/source-inputs.json').read_text())['projects'].items()}
project_ids={'Microsoft.CodeAnalysis':'Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.CSharp':'Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces':'Microsoft.CodeAnalysis.Workspaces.Common'}
for name,original in names.items():
    folder=out/name;folder.mkdir()
    version='4.14.0';commit='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b';source_root=roslyn
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    namespace=evaluated[name]['properties']['RootNamespace'] or name
    values=dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',AssemblyName=name,RootNamespace=namespace,PackageId='Microsoft.CodeAnalysis.Workspaces.Common' if name=='Microsoft.CodeAnalysis.Workspaces' else name,
                Version=version,AssemblyVersion=version+'.0',FileVersion=version+'.0',InformationalVersion=version+'+'+commit,
                IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',
                NuGetAudit='false',Nullable='enable',LangVersion='preview',AllowUnsafeBlocks='true',UseSharedCompilation='false',
                CscToolPath=native(compiler),CscToolExe='csc50.cmd',SignAssembly='true',PublicSign='true',
                AssemblyOriginatorKeyFile='../MicrosoftShared.pubkey',
                DefineConstants=evaluated[name]['properties']['DefineConstants'],NoWarn='CS0436;CS0618;SYSLIB0051;SYSLIB0050;RSEXPERIMENTAL005',
                PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/roslyn',RepositoryCommit=commit)
    for k,v in values.items():E.SubElement(pg,k).text=v
    items=E.SubElement(tree,'ItemGroup')
    selected=list(dict.fromkeys(posix(i['full_path']) for i in evaluated[name]['items']['Compile']))
    assert selected and all(p.is_file() for p in selected)
    assert not any('/Storage/SQLite/' in str(p) for p in selected)
    resources={posix(i['full_path']):i['metadata'] for i in evaluated[name]['items']['EmbeddedResource']}
    for path,metadata in resources.items():resource(items,folder,path,metadata,namespace,source_root)
    for path in selected:E.SubElement(items,'Compile',Include=native(path))
    deps={};minimums={}
    for item in evaluated[name]['items']['PackageReference']:
        ident=item['identity']
        if ident=='NETStandard.Library':continue
        assert ident in versions,(name,ident)
        minimums[ident]=versions[ident]
        deps[ident]=maintenance.get(ident,'9.0.0' if ident in ['Microsoft.Bcl.AsyncInterfaces','System.Threading.Channels','System.IO.Pipelines','System.Composition'] else versions[ident])
    for item in evaluated[name]['items']['ProjectReference']:
        ident=Path(item['full_path'].replace('\\','/')).stem;assert ident in project_ids,(name,ident)
        deps[project_ids[ident]]='4.14.0'
    for dep,dep_version in deps.items():
        E.SubElement(items,'PackageReference',Include=dep,Version='['+dep_version+']',**({'PrivateAssets':'compile'} if dep=='Humanizer.Core' else {}))
    original_xml=E.parse(original);friends=[]
    for kind in ['InternalsVisibleTo','RestrictedInternalsVisibleTo']:
        raw={e.get('Include'):e.attrib for e in original_xml.iter(kind)}
        for item in evaluated[name]['items'][kind]:
            metadata=raw.get(item['identity'],item['metadata']);key=public_key(metadata.get('Key',''))
            friends.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+key)+')]')
            if kind=='RestrictedInternalsVisibleTo':
                ns=metadata.get('Namespace') or 'Microsoft.CodeAnalysis.ExternalAccess.'+metadata['Partner']+'.Api'
                friends.append('[assembly: System.Runtime.CompilerServices.RestrictedInternalsVisibleTo('+json.dumps(item['identity'])+', '+json.dumps(ns)+')]')
    if friends:
        (folder/'Friends.Generated.cs').write_text('\n'.join(dict.fromkeys(friends))+'\n');E.SubElement(items,'Compile',Include='Friends.Generated.cs')
    for file in ['License.txt','THIRD-PARTY-NOTICES.txt']:E.SubElement(items,'None',Include=native(roslyn/file),Pack='true',PackagePath='')
    capture=E.SubElement(tree,'Target',Name='CaptureOriginalShippingInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree,folder/'Build.csproj')
    resource_hashes={p.relative_to(source_root).as_posix():sha(p) for path in resources for p in [path,*sorted((path.parent/'xlf').glob(path.stem+'.*.xlf'))]}
    records[name]=dict(source_repository='roslyn',original_project=original.relative_to(source_root).as_posix(),
                       original_project_sha256=sha(original),original_cs={p.relative_to(source_root).as_posix():sha(p) for p in selected},
                       original_resources=resource_hashes,production_cs_changes=0,original_supported_framework='netstandard2.0',configuration='Release',framework='netstandard2.0',
                       original_package_minimums=minimums,resolved_dependencies=deps,friend_declarations=len(friends),original_sqlite_source_build_exclusion=True)

feed=out/'feed';feed.mkdir()
(out/'source-inputs.json').write_text(json.dumps(dict(roslyn_version='4.14.0',roslyn_commit='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b',source_archive_sha256=sha(root/'roslyn-4.14.0-8edf7bcd.tar.gz'),projects=records,original_versions_sha256=sha(roslyn/'eng/Versions.props'),original_central_packages_sha256=sha(roslyn/'eng/Directory.Packages.props'),original_settings_sha256=sha(roslyn/'eng/targets/Settings.props'),full_dependency_goal_complete=False),indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
cfg=E.Element('configuration');sources=E.SubElement(cfg,'packageSources');E.SubElement(sources,'clear')
for i,path in enumerate([feed,Path('/clang64/lib/dotnet/library-packs')]):E.SubElement(sources,'add',key='source'+str(i),value=native(path))
save(cfg,out/'NuGet.config')
(out/'tool-inputs.json').write_text(json.dumps({str(p):dict(owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip(),sha256=sha(p)) for p in [compiler/n for n in ['CompilerHost.dll','Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]},indent=2)+'\n')
print('Prepared original Standard2.0 Workspaces source projects',{n:len(r['original_cs']) for n,r in records.items()},'resource sets',len(localizations),flush=True)
