"""Prepare original runtime9 netstandard2.0 dependencies and a source interop bootstrap."""
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(),out
out.mkdir(parents=True)
here=Path(__file__).resolve().parent
source=root/'roslyn-deps9-1/runtime-source';libs=source/'src/libraries'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'runtime-v9.0.0.tar.gz')=='32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
assert json.loads((root/'roslyn-deps9-1/source-inputs.json').read_text())['runtime_commit']=='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3'
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
names=['System.Collections.Immutable','System.Reflection.Metadata','System.Composition.AttributedModel','System.Composition.Runtime',
       'System.Composition.Hosting','System.Composition.Convention','System.Composition.TypedParts','Microsoft.Bcl.AsyncInterfaces',
       'System.IO.Pipelines','System.Threading.Channels','System.Text.Encoding.CodePages']
projects={n:libs/n/'src'/(n+'.csproj') for n in names}
interop=libs/'System.Runtime.InteropServices/gen'
projects.update({'bootstrap:Microsoft.Interop.SourceGeneration':interop/'Microsoft.Interop.SourceGeneration/Microsoft.Interop.SourceGeneration.csproj',
                 'bootstrap:Microsoft.Interop.LibraryImportGenerator':interop/'LibraryImportGenerator/LibraryImportGenerator.csproj'})
# Retain the original conditional source-sharing policies without importing
# unrelated repository build, package and analyzer tasks into this bootstrap.
shared=E.Element('Project')
original_targets=E.parse(libs/'Directory.Build.targets').getroot()
for item in original_targets:
    text=E.tostring(item,encoding='unicode')
    if item.tag in {'ItemGroup','Choose'} and any(s in text for s in ['NullableAttributes.cs','PlatformAttributes.cs','System\\ObsoleteAttribute.cs','System\\Index.cs']):shared.append(copy.deepcopy(item))
assert len(shared)==4
save(shared,out/'original-shared-sources.targets')
wrappers={};key_policies={}
for name,original in projects.items():
    folder=out/'evaluation'/name.replace(':','-');folder.mkdir(parents=True)
    body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
    tree=E.fromstring(body);tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile','EmbeddedResource','ProjectReference'}:continue
        for attr in ['Include','Remove','Update']:
            value=item.get(attr,'').replace('\\','/')
            if value and '$(' not in value:item.set(attr,native(original.parent/value))
    save(tree,folder/'upstream.proj')
    bootstrap=name.startswith('bootstrap:')
    policy=original.parent.parent/'Directory.Build.props'
    key=E.parse(policy).findtext('.//StrongNameKeyId') if policy.is_file() else None
    key=E.fromstring(body).findtext('.//StrongNameKeyId') or key or 'Open'
    key_policies[name]=dict(key=key,policy=policy.relative_to(source).as_posix() if policy.is_file() else None)
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(TargetFramework='net8.0' if bootstrap else 'netstandard2.0',TargetFrameworkIdentifier='.NETCoreApp' if bootstrap else '.NETStandard',
                    ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',Nullable='enable',
                    NetCoreAppCurrent='net9.0',NetCoreAppPrevious='net8.0',NetCoreAppMinimum='net8.0',NetFrameworkMinimum='net462',
                    CommonPath=native(libs/'Common/src')+'/',LibrariesProjectRoot=native(libs)+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/',
                    IsSourceProject='true',StrongNameKeyId=key,MicrosoftCodeAnalysisVersion_LatestVS='4.8.0',SystemMemoryVersion='4.5.5',SystemBuffersVersion='4.5.1',SystemRuntimeCompilerServicesUnsafeVersion='6.0.0',SystemThreadingTasksExtensionsVersion='4.5.4').items():E.SubElement(pg,k).text=v
    if bootstrap:
        items=E.SubElement(wrapper,'ItemGroup')
        for file in sorted(original.parent.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(file))
    E.SubElement(wrapper,'Import',Project='upstream.proj')
    E.SubElement(wrapper,'Import',Project=native(out/'original-shared-sources.targets'))
    path=folder/(original.stem+'.csproj');save(wrapper,path);wrappers[name]=native(path)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
env=dict(os.environ,MSBuildSDKsPath=native(Path('/clang64/lib/dotnet/sdk/8.0.131/Sdks')),
         MSBUILD_EXE_PATH=native(Path('/clang64/lib/dotnet/sdk/8.0.131/MSBuild.dll')),MSBuildEnableWorkloadResolver='false')
tool=root/'roslyn414-1/evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'
with (out/'evaluation.log').open('w') as log:
    subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(tool),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for key in ['Microsoft','Open']:(out/(key+'.pubkey')).write_bytes(bytes.fromhex((here/'inputs'/(key+'.pubkey.hex')).read_text()))
maintenance_versions={n:r['version'] for n,r in json.loads((root/'maintenance20-1/source-inputs.json').read_text())['projects'].items()}
records={};localizations=[]
for name,original in projects.items():
    bootstrap=name.startswith('bootstrap:');assembly=name.removeprefix('bootstrap:')
    folder=out/('bootstrap' if bootstrap else 'libraries')/assembly;folder.mkdir(parents=True)
    selected=[posix(i['full_path']) for i in evaluated[name]['items']['Compile']]
    resource=interop/'Common/Resources/Strings.resx' if bootstrap else original.parent/'Resources/Strings.resx'
    if resource.is_file():selected.append(libs/'Common/src/System/SR.cs')
    if not bootstrap:
        selected.extend([libs/'System.Private.CoreLib/src/System/Runtime/InteropServices/LibraryImportAttribute.cs',libs/'System.Private.CoreLib/src/System/Runtime/InteropServices/StringMarshalling.cs'])
    assert len(selected)==len(set(selected)) and all(p.is_file() for p in selected),name
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    key=key_policies[name]['key'];assert key in ['Open','Microsoft'],(name,key)
    for k,v in dict(TargetFramework='net8.0' if bootstrap else 'netstandard2.0',AssemblyName=assembly,PackageId=assembly,Version='9.0.0',AssemblyVersion='9.0.0.0',FileVersion='9.0.0.0',InformationalVersion='9.0.0+9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',
                    IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',Nullable=E.parse(original).findtext('.//Nullable') or 'enable',AllowUnsafeBlocks='true',LangVersion='preview',
                    EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/(key+'.pubkey')),
                    DefineConstants=evaluated[name]['properties']['DefineConstants'],PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/runtime',RepositoryCommit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',IsPackable='false' if bootstrap else 'true',
                    CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2') if bootstrap else root/'cdac-bootstrap5/compiler'),CscToolExe='csc49.cmd' if bootstrap else 'csc50.cmd',
                    EmitCompilerGeneratedFiles='true',CompilerGeneratedFilesOutputPath='$(IntermediateOutputPath)generated',CopyLocalLockFileAssemblies='true' if bootstrap else 'false').items():E.SubElement(pg,k).text=v
    ig=E.SubElement(tree,'ItemGroup')
    for file in selected:E.SubElement(ig,'Compile',Include=native(file))
    dependencies={};original_packages={}
    for i in evaluated[name]['items']['PackageReference']:
        ident=i['identity'];minimum=i['metadata'].get('Version','')
        if ident=='NETStandard.Library':
            assert minimum=='2.0.3';continue
        original_packages[ident]=minimum
        if bootstrap:continue
        assert ident in maintenance_versions,(name,ident)
        dependencies[ident]=maintenance_versions[ident]
    for item in evaluated[name]['items']['ProjectReference']:
        ident=Path(item['full_path'].replace('\\','/')).stem
        if bootstrap:
            E.SubElement(ig,'ProjectReference',Include=native(out/'bootstrap'/('Microsoft.Interop.SourceGeneration' if ident=='Microsoft.Interop.SourceGeneration' else ident)/'Build.csproj'))
        else:
            assert ident in names,(name,ident);dependencies[ident]='9.0.0'
    if bootstrap:
        E.SubElement(ig,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.9.2]')
    else:
        for ident,version in dependencies.items():E.SubElement(ig,'PackageReference',Include=ident,Version='['+version+']')
        for analyzer in ['Microsoft.Interop.SourceGeneration','Microsoft.Interop.LibraryImportGenerator']:
            E.SubElement(ig,'Analyzer',Include=native(out/'bootstrap'/analyzer/'bin/Release/net8.0'/(analyzer+'.dll')))
        E.SubElement(pg,'LibraryImportGenerator_UseMarshalType').text='true'
        E.SubElement(tree,'Import',Project=native(interop/'LibraryImportGenerator/Microsoft.Interop.LibraryImportGenerator.props'))
    extra_resources={}
    for item in evaluated[name]['items']['EmbeddedResource']:
        file=posix(item['full_path']);assert file.is_file(),file
        if file==resource:continue
        E.SubElement(ig,'EmbeddedResource',Include=native(file),LogicalName=item['metadata'].get('LogicalName') or file.name)
        extra_resources[file.relative_to(source).as_posix()]=sha(file)
    if resource.is_file():
        logical='FxResources.'+assembly+'.SR'
        code=['#nullable enable','namespace FxResources.'+assembly+' { internal static class SR {} }','namespace System { internal static partial class SR {','internal static global::System.Resources.ResourceManager ResourceManager { get; } = new global::System.Resources.ResourceManager("'+logical+'",typeof(FxResources.'+assembly+'.SR).Assembly);']
        for item in E.parse(resource).iter('data'):
            ident=item.get('name');assert ident.isidentifier();code.append('internal static string @'+ident+' => GetResourceString("'+ident+'");')
        code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
        E.SubElement(ig,'Compile',Include='SR.Generated.cs');E.SubElement(ig,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
        localizations.append(dict(assembly=name,logical_name=logical,culture='',strings={e.get('name'):e.findtext('value') or '' for e in E.parse(resource).iter('data')}))
        extra_resources[resource.relative_to(source).as_posix()]=sha(resource)
        ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
        for xlf_file in sorted((resource.parent/'xlf').glob(resource.stem+'.*.xlf')):
            xlf=E.parse(xlf_file);culture=xlf.find('x:file',ns).get('target-language')
            values={e.get('id'):''.join(e.find('x:target',ns).itertext()) for e in xlf.findall('.//x:trans-unit',ns) if e.find('x:target',ns) is not None}
            localized=E.parse(resource)
            for e in localized.iter('data'):
                if e.get('name') in values:e.find('value').text=values[e.get('name')]
            target=folder/('Strings.'+culture+'.resx');localized.write(target,encoding='utf-8',xml_declaration=True)
            E.SubElement(ig,'EmbeddedResource',Include=target.name,LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
            localizations.append(dict(assembly=name,logical_name=logical,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))
            extra_resources[xlf_file.relative_to(source).as_posix()]=sha(xlf_file)
    for file in [source/'LICENSE.TXT',source/'THIRD-PARTY-NOTICES.TXT',original.parent/'PACKAGE.md']:
        if file.is_file():E.SubElement(ig,'None',Include=native(file),Pack='true',PackagePath='')
    capture=E.SubElement(tree,'Target',Name='CaptureCompilerInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:
        E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    save(tree,folder/'Build.csproj')
    records[name]=dict(original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},resource_files_sha256=extra_resources,
                       key=key,key_policy=key_policies[name]['policy'],original_package_minimums=original_packages,resolved_dependencies=dependencies,
                       original_supported_framework='netstandard2.0',bootstrap_host_framework='net8.0' if bootstrap else None,production_cs_changes=0)
meta=E.Element('package');md=E.SubElement(meta,'metadata')
for k,v in dict(id='System.Composition',version='9.0.0',authors='.NET Foundation',description='Original source composition dependency metapackage.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/runtime',commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3')
group=E.SubElement(E.SubElement(md,'dependencies'),'group',targetFramework='.NETStandard2.0')
for n in names:
    if n.startswith('System.Composition.'):E.SubElement(group,'dependency',id=n,version='[9.0.0]')
save(meta,out/'System.Composition.nuspec')
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for name,path in [('private',out/'feed'),('maintenance',root/'maintenance20-1/feed'),('standard',root/'netstandard20-2/feed'),('installed-source',Path('/clang64/lib/dotnet/library-packs'))]:E.SubElement(feeds,'add',key=name,value=native(path))
save(config,out/'NuGet.config');(out/'feed').mkdir()
(out/'source-inputs.json').write_text(json.dumps(dict(runtime_commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',source_root=native(source),projects=records,order=names,
    shared_sources_policy_sha256=sha(libs/'Directory.Build.targets'),generator_policy_sha256=sha(source/'eng/generators.targets'),composition_original_project_sha256=sha(libs/'System.Composition/src/System.Composition.csproj'),full_dependency_goal_complete=False),indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
print('Prepared original source9 graph', {n:len(r['original_cs']) for n,r in records.items()},flush=True)
