"""Prepare the exact Roslyn5.0 compiler libraries and their original generators."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:3])
resume = len(sys.argv) == 4 and sys.argv[3] == '--resume'
assert out.exists() if resume else not out.exists(), out
out.mkdir(parents=True, exist_ok=resume)
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
archive = root / 'roslyn-5.0.0-6c4a46a3.tar.gz'
assert sha(archive) == '7b0bfa1c049eeddf3257ad61b28eca11c259296d478edd4cf58767b2ed9184c4'
commit = '6c4a46a31302167b425d5e0a31ea83c9a9aa1d09'
native_root = subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(path):
    path=Path(path).resolve()
    if path.is_relative_to(root):return native_root+'/'+path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(path)],text=True).strip()
subprocess.run(['/clang64/bin/python.exe',native(here/'extract-source.py'),native(archive),native(out)],check=True)
source=out/'roslyn-source'
removed=json.loads((out/'extracted-source-inputs.json').read_text())['removed_binary_inputs']
def posix(path):
    path=path.replace('\\','/');assert path.lower().startswith(native_root.lower()+'/')
    return root/path[len(native_root)+1:]
compiler = Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
key = bytes.fromhex((here/'inputs/MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Roslyn.public.snk').write_bytes(key)
records,localizations,generator_tools={},[],{}
def project(folder,name,exe=False):
    folder.mkdir(parents=True, exist_ok=resume)
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace=name,OutputType='Exe' if exe else 'Library',
                UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',WarningsAsErrors='NU1608',
                AllowUnsafeBlocks='true',Nullable='enable',LangVersion='preview',UseSharedCompilation='false',
                CscToolPath=native(compiler),CscToolExe='csc50.cmd',Version='5.0.0',AssemblyVersion='5.0.0.0',
                FileVersion='5.0.0.0',InformationalVersion='5.0.0+'+commit,IncludeSourceRevisionInInformationalVersion='false')
    for k,v in values.items():E.SubElement(pg,k).text=v
    return tree,pg,E.SubElement(tree,'ItemGroup')
def save(tree,path):
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
tools=source/'src/Tools/Source/CompilerGeneratorTools/Source'
for name in ['CSharpSyntaxGenerator','BoundTreeGenerator','CSharpErrorFactsGenerator']:
    folder=out/name;tree,pg,items=project(folder,name,True)
    selected=[p for p in sorted((tools/name).rglob('*.cs')) if p.name not in {'SourceGenerator.cs','CachingSourceGenerator.cs'}]
    if name=='CSharpSyntaxGenerator':
        selected += [source/'src/Compilers'/p for p in ['CSharp/Portable/Syntax/SyntaxKind.cs','CSharp/Portable/Syntax/SyntaxKindFacts.cs','CSharp/Portable/Declarations/DeclarationModifiers.cs','Core/Portable/Symbols/WellKnownMemberNames.cs']]
    for path in selected:E.SubElement(items,'Compile',Include=native(path))
    capture=E.SubElement(tree,'Target',Name='CaptureActualCompilerInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree,folder/'Build.csproj')
    generator_tools[name]=dict(original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},production_cs_changes=0)

wrappers={}
for name,language in [('Microsoft.CodeAnalysis','Core'),('Microsoft.CodeAnalysis.CSharp','CSharp')]:
    main=source/'src/Compilers'/language/'Portable';original=main/(name+'.csproj')
    folder=out/'evaluation'/name;folder.mkdir(parents=True,exist_ok=resume)
    body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(main)+'/')
    upstream=E.ElementTree(E.fromstring(body));upstream.getroot().attrib.pop('Sdk')
    for item in upstream.iter():
        for attribute in ['Include','Remove','Update','Project']:
            if item.tag not in {'Compile','Import','ProjectReference','EmbeddedResource'} or attribute not in item.attrib:continue
            value=item.get(attribute).replace('\\','/')
            if '$(' not in value and not value.startswith('/') and not (len(value)>1 and value[1]==':'):
                item.set(attribute,native(main/value))
    save(upstream.getroot(),folder/'upstream.proj')
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',NetRoslynSourceBuild='net8.0;net9.0',ImportDirectoryBuildProps='false',
                    ImportDirectoryBuildTargets='false',EnableDefaultItems='false',DotNetBuildSourceOnly='true',
                    RootNamespace=name,DefineConstants='$(DefineConstants);DOTNET_BUILD_FROM_SOURCE',
                    CompilerGeneratedFilesOutputPath=native(main/'Generated')).items():E.SubElement(pg,k).text=v
    E.SubElement(wrapper,'Import',Project=native(source/'eng/Versions.props'))
    E.SubElement(wrapper,'Import',Project=native(source/'eng/Packages.props'))
    items=E.SubElement(wrapper,'ItemGroup')
    for path in sorted(main.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(path))
    for path in sorted(main.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(path))
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    save(wrapper,folder/(name+'.csproj'));wrappers[name]=native(folder/(name+'.csproj'))
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
tool=out/'evaluation-tool';tree,pg,items=project(tool,'EvaluateRoslynProjects',True)
E.SubElement(items,'Compile',Include=native(here/'inputs/EvaluateRoslynProjects.cs'))
sdk=Path('/clang64/lib/dotnet/sdk/8.0.131')
sdk_native=subprocess.check_output(['cygpath','-am',str(sdk)],text=True).strip()
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    r=E.SubElement(items,'Reference',Include=name);E.SubElement(r,'HintPath').text=sdk_native+'/'+name+'.dll'
save(tree,tool/'Build.csproj')
feed=Path('/clang64/lib/dotnet/library-packs')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source-private" value="'+native(out/'feed')+'"/><add key="installed-source" value="'+native(feed)+'"/></packageSources></configuration>\n')
dotnet='/clang64/lib/dotnet/dotnet.exe'
env=dict(os.environ,MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
with (out/'evaluation-build.log').open('w') as log:
    subprocess.run([dotnet,'build',native(tool/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
env.update(MSBuildSDKsPath=sdk_native+'/Sdks',MSBUILD_EXE_PATH=sdk_native+'/MSBuild.dll')
with (out/'evaluation.log').open('w') as log:
    subprocess.run([dotnet,native(tool/'bin/Release/net8.0/EvaluateRoslynProjects.dll'),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for item in evaluated.values():assert 'DEBUG' not in item['properties']['DefineConstants'].split(';')
properties={}
for filename in ['eng/Version.Details.props','eng/Versions.props']:
    for group in E.parse(source/filename).getroot().findall('PropertyGroup'):
        if "'$(DotNetBuildSourceOnly)' != 'true'" in group.get('Condition',''):continue
        for item in group:
            if item.text:properties[item.tag]=item.text.strip()
def resolve_version(value):
    seen=set()
    while value.startswith('$(') and value.endswith(')'):
        assert value not in seen,('Version alias cycle',value)
        seen.add(value);value=properties.get(value[2:-1],'')
    return value
package_versions={}
for item in E.parse(source/'eng/Packages.props').iter('PackageVersion'):
    version=item.get('Version','')
    version=resolve_version(version)
    if version:package_versions[item.get('Include')]=version
settings=E.parse(source/'eng/targets/Settings.props')
def key_value(name):
    value=settings.findtext('.//'+name)
    while value and value.startswith('$(') and value.endswith(')'):value=settings.findtext('.//'+value[2:-1])
    assert value and all(c in '0123456789abcdefABCDEF' for c in value),(name,value)
    return value
assert key==bytes.fromhex(key_value('MicrosoftSharedPublicKey'))
maintenance={n:r['version'] for n,r in json.loads(Path('/clang64/share/doc/dotnet-maintenance-netstandard10/source-inputs.json').read_text())['projects'].items()}
for name,language in [('Microsoft.CodeAnalysis','Core'),('Microsoft.CodeAnalysis.CSharp','CSharp')]:
    folder=out/name;tree,pg,items=project(folder,name)
    pg.find('TargetFramework').text='netstandard2.0'
    for k,v in dict(SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='../Roslyn.public.snk',
                    PackageId='Microsoft.CodeAnalysis.Common' if language=='Core' else name,PackageLicenseExpression='MIT',
                    RepositoryUrl='https://github.com/dotnet/roslyn',RepositoryCommit=commit,
                    DefineConstants=evaluated[name]['properties']['DefineConstants']+';DOTNET_BUILD_FROM_SOURCE',NoWarn='CS0436;CS0618;SYSLIB0051;SYSLIB0050;RSEXPERIMENTAL005').items():E.SubElement(pg,k).text=v
    selected=[posix(item['full_path']) for item in evaluated[name]['items']['Compile']]
    if language=='CSharp':selected=[p for p in selected if not p.is_relative_to(source/'src/Compilers/CSharp/Portable/Generated')]
    selected=list(dict.fromkeys(selected));assert all(p.is_file() for p in selected)
    for path in selected:E.SubElement(items,'Compile',Include=native(path))
    if language=='CSharp':E.SubElement(items,'Compile',Include=native(out/'generated/*.cs'))
    dependencies={};minimums={}
    for item in evaluated[name]['items']['PackageReference']:
        ident=item['identity']
        if ident=='NETStandard.Library':continue
        assert ident in package_versions,(name,ident)
        minimums[ident]=package_versions[ident]
        dependencies[ident]=maintenance.get(ident,'9.0.0' if ident in ['System.Collections.Immutable','System.Reflection.Metadata','System.Text.Encoding.CodePages'] else package_versions[ident])
    if language=='CSharp':dependencies['Microsoft.CodeAnalysis.Common']='5.0.0'
    for ident,version in dependencies.items():E.SubElement(items,'PackageReference',Include=ident,Version='['+version+']')
    for file in ['License.txt','THIRD-PARTY-NOTICES.txt']:E.SubElement(items,'None',Include=native(source/file),Pack='true',PackagePath='')
    resources={}
    for item in evaluated[name]['items']['EmbeddedResource']:
        path=posix(item['full_path']);resources[path]=item['metadata']
    for path,metadata in resources.items():
        if path.suffix!='.resx':
            relative=path.relative_to(source/'src/Compilers'/language/'Portable').as_posix().replace('/','.')
            E.SubElement(items,'EmbeddedResource',Include=native(path),LogicalName=name+'.'+relative);continue
        namespace=metadata.get('Namespace') or name
        classname=metadata.get('ClassName') or path.stem
        if '.' in classname:namespace,_,classname=classname.rpartition('.')
        logical=(metadata.get('LogicalName') or metadata.get('ManifestResourceName') or namespace+'.'+path.stem).removesuffix('.resources')
        code=['#nullable enable','namespace '+namespace+' { internal static class '+classname+' {',
              'internal static global::System.Resources.ResourceManager ResourceManager { get; } = new global::System.Resources.ResourceManager('+json.dumps(logical)+', typeof('+classname+').Assembly);',
              'internal static global::System.Globalization.CultureInfo? Culture { get; set; }']
        for item in E.parse(path).iter('data'):
            key_name=item.get('name');assert key_name.isidentifier(),key_name
            code.append('internal static string @'+key_name+' => ResourceManager.GetString('+json.dumps(key_name)+', Culture)!;')
        code.append('}}');generated=folder/(namespace+'.'+classname+'.Generated.cs');generated.write_text('\n'.join(code)+'\n')
        E.SubElement(items,'Compile',Include=generated.name);E.SubElement(items,'EmbeddedResource',Include=native(path),LogicalName=logical+'.resources')
        localizations.append(dict(assembly=name,logical_name=logical,culture='',strings={i.get('name'):i.findtext('value') or '' for i in E.parse(path).iter('data')}))
        ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
        for translation in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
            xlf=E.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
            values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
            localized=E.parse(path)
            for i in localized.iter('data'):
                if i.get('name') in values:i.find('value').text=values[i.get('name')]
            target=folder/(logical+'.'+culture+'.resx');localized.write(target,encoding='utf-8',xml_declaration=True)
            E.SubElement(items,'EmbeddedResource',Include=target.name,LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
            localizations.append(dict(assembly=name,logical_name=logical,culture=culture,strings={i.get('name'):i.findtext('value') or '' for i in localized.iter('data')}))
    friends=[]
    original_friends={item.get('Include'):item.get('Key','') for item in E.parse(source/'src/Compilers'/language/'Portable'/(name+'.csproj')).iter('InternalsVisibleTo')}
    for item in evaluated[name]['items']['InternalsVisibleTo']:
        value=original_friends.get(item['identity'],item['metadata'].get('Key',''))
        public=key_value(value[2:-1]) if value.startswith('$(') else value or key.hex()
        friends.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+public)+')]')
    if language=='CSharp':friends.append('[assembly: Microsoft.CodeAnalysis.CommitHash('+json.dumps(commit)+')]')
    (folder/'Friends.Generated.cs').write_text('\n'.join(dict.fromkeys(friends))+'\n');E.SubElement(items,'Compile',Include='Friends.Generated.cs')
    capture=E.SubElement(tree,'Target',Name='CaptureActualCompilerInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree,folder/'Build.csproj')
    records[name]=dict(original_project='src/Compilers/'+language+'/Portable/'+name+'.csproj',original_project_sha256=sha(source/'src/Compilers'/language/'Portable'/(name+'.csproj')),
                       original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},production_cs_changes=0,
                       original_resources={p.relative_to(source).as_posix():sha(p) for p in resources},friend_declarations=len(friends),
                       original_package_minimums=minimums,resolved_dependencies=dependencies,configuration='Release',framework='netstandard2.0')
(out/'source-inputs.json').write_text(json.dumps(dict(roslyn_version='5.0.0',roslyn_commit=commit,source_archive_sha256=sha(archive),removed_binary_inputs=removed,projects=records,generator_tools=generator_tools,source_root=native(source),original_versions_sha256=sha(source/'eng/Versions.props'),original_version_details_sha256=sha(source/'eng/Version.Details.props'),original_central_packages_sha256=sha(source/'eng/Packages.props'),original_settings_sha256=sha(source/'eng/targets/Settings.props'),full_dependency_goal_complete=False),indent=2)+'\n')
tool_inputs={str(p):dict(owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip(),sha256=sha(p)) for p in [compiler/n for n in ['CompilerHost.dll','Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]}
(out/'tool-inputs.json').write_text(json.dumps(tool_inputs,indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
print('Prepared original Roslyn5.0 source projects:',{name:len(r['original_cs']) for name,r in records.items()},'localized payloads',len(localizations))
