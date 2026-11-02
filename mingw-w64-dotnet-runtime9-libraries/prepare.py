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
source=out/'runtime-source';libs=source/'src/libraries'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'runtime-v9.0.0.tar.gz')=='32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
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
subprocess.run(['/clang64/bin/python.exe',native(here/'extract-source.py'),native(root/'runtime-v9.0.0.tar.gz'),native(out)],check=True)
projects={n:libs/n/'src'/(n+'.csproj') for n in names}
projects.update({'baseline:'+n:libs/n/'src'/(n+'.csproj') for n in names if n.startswith('System.Composition.')})
projects['forwarder:Microsoft.Bcl.AsyncInterfaces']=projects['Microsoft.Bcl.AsyncInterfaces']
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
    bootstrap=name.startswith('bootstrap:');baseline=name.startswith('baseline:');net8=bootstrap or baseline
    forwarder=name.startswith('forwarder:');tfm='net8.0' if net8 else 'netstandard2.1' if forwarder else 'netstandard2.0'
    policy=original.parent.parent/'Directory.Build.props'
    key=E.parse(policy).findtext('.//StrongNameKeyId') if policy.is_file() else None
    key=E.fromstring(body).findtext('.//StrongNameKeyId') or key or 'Open'
    key_policies[name]=dict(key=key,policy=policy.relative_to(source).as_posix() if policy.is_file() else None)
    wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework=tfm,TargetFrameworkIdentifier='.NETCoreApp' if net8 else '.NETStandard',
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
tool=out/'evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'
helper=out/'evaluation-tool';helper.mkdir()
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='EvaluateRoslynProjects',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(project,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/EvaluateProjects.cs'))
for ident in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
 E.SubElement(E.SubElement(items,'Reference',Include=ident),'HintPath').text=native(Path('/clang64/lib/dotnet/sdk/8.0.131')/(ident+'.dll'))
save(project,helper/'Build.csproj');(helper/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env.update(DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
with (helper/'build.log').open('w') as log:
 subprocess.run(['/clang64/lib/dotnet/dotnet.exe','build',native(helper/'Build.csproj'),'-c','Release','--configfile',native(helper/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (out/'evaluation.log').open('w') as log:
    subprocess.run(['/clang64/lib/dotnet/dotnet.exe',native(tool),native(out/'wrappers.json'),native(out/'evaluated.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
evaluated=json.loads((out/'evaluated.json').read_text())
for key in ['Microsoft','Open']:(out/(key+'.pubkey')).write_bytes(bytes.fromhex((here/'inputs'/(key+'.pubkey.hex')).read_text()))
maintenance_versions={n:r['version'] for n,r in json.loads((Path('/clang64/share/doc/dotnet-maintenance-netstandard/source-inputs.json')).read_text())['projects'].items()}
records={};localizations=[]
for name,original in projects.items():
    bootstrap=name.startswith('bootstrap:');baseline=name.startswith('baseline:');net8=bootstrap or baseline;assembly=name.split(':')[-1]
    forwarder=name.startswith('forwarder:');tfm='net8.0' if net8 else 'netstandard2.1' if forwarder else 'netstandard2.0'
    folder=out/('bootstrap' if bootstrap else 'baseline-net8' if baseline else 'forwarder-netstandard21' if forwarder else 'libraries')/assembly;folder.mkdir(parents=True)
    selected=[posix(i['full_path']) for i in evaluated[name]['items']['Compile']]
    resource=interop/'Common/Resources/Strings.resx' if bootstrap else original.parent/'Resources/Strings.resx'
    if resource.is_file():selected.append(libs/'Common/src/System/SR.cs')
    if not net8 and not forwarder:
        selected.extend([libs/'System.Private.CoreLib/src/System/Runtime/InteropServices/LibraryImportAttribute.cs',libs/'System.Private.CoreLib/src/System/Runtime/InteropServices/StringMarshalling.cs'])
    assert len(selected)==len(set(selected)) and all(p.is_file() for p in selected),name
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    key=key_policies[name]['key'];assert key in ['Open','Microsoft'],(name,key)
    assert 'DEBUG' not in evaluated[name]['properties']['DefineConstants'].split(';'),name
    for k,v in dict(TargetFramework=tfm,AssemblyName=assembly,PackageId=assembly,Version='9.0.0',AssemblyVersion='9.0.0.0',FileVersion='9.0.0.0',InformationalVersion='9.0.0+9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',
                    IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',Nullable=E.parse(original).findtext('.//Nullable') or 'enable',AllowUnsafeBlocks='true',LangVersion='preview',
                    EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/(key+'.pubkey')),
                    DefineConstants=evaluated[name]['properties']['DefineConstants'],PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/runtime',RepositoryCommit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',IsPackable='false' if net8 or forwarder else 'true',
                    CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2') if bootstrap else Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc49.cmd' if bootstrap else 'csc50.cmd',
                    EmitCompilerGeneratedFiles='true',CompilerGeneratedFilesOutputPath='$(IntermediateOutputPath)generated',CopyLocalLockFileAssemblies='true' if bootstrap else 'false',GenerateAssemblyConfigurationAttribute='false',GenerateNeutralResourcesLanguageAttribute='false').items():E.SubElement(pg,k).text=v
    ig=E.SubElement(tree,'ItemGroup')
    policy=source/key_policies[name]['policy'] if key_policies[name]['policy'] else None
    cls=E.parse(original).findtext('.//CLSCompliant') or (E.parse(policy).findtext('.//CLSCompliant') if policy else None) or 'true'
    if cls=='true':
        attr=E.SubElement(ig,'AssemblyAttribute',Include='System.CLSCompliantAttribute');E.SubElement(attr,'_Parameter1').text='true';E.SubElement(attr,'_Parameter1_IsLiteral').text='true'
    for typ,value,literal in [('System.Reflection.AssemblyDefaultAliasAttribute',assembly,False),('System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute','System.Runtime.InteropServices.DllImportSearchPath.AssemblyDirectory | System.Runtime.InteropServices.DllImportSearchPath.System32',True)]:
        attr=E.SubElement(ig,'AssemblyAttribute',Include=typ);E.SubElement(attr,'_Parameter1').text=value
        if literal:E.SubElement(attr,'_Parameter1_IsLiteral').text='true'
    for ident in ['PreferInbox','Serviceable']:E.SubElement(ig,'AssemblyMetadata',Include=ident,Value='True')
    if resource.is_file() and not bootstrap:
        attr=E.SubElement(ig,'AssemblyAttribute',Include='System.Resources.NeutralResourcesLanguageAttribute');E.SubElement(attr,'_Parameter1').text='en-US'
    for file in selected:E.SubElement(ig,'Compile',Include=native(file))
    dependencies={};original_packages={}
    for i in evaluated[name]['items']['PackageReference']:
        ident=i['identity'];minimum=i['metadata'].get('Version','')
        if ident=='NETStandard.Library':
            assert minimum=='2.0.3';continue
        original_packages[ident]=minimum
        if net8:continue
        assert ident in maintenance_versions,(name,ident)
        dependencies[ident]=maintenance_versions[ident]
    for item in evaluated[name]['items']['ProjectReference']:
        ident=Path(item['full_path'].replace('\\','/')).stem
        if bootstrap:
            E.SubElement(ig,'ProjectReference',Include=native(out/'bootstrap'/('Microsoft.Interop.SourceGeneration' if ident=='Microsoft.Interop.SourceGeneration' else ident)/'Build.csproj'))
        elif baseline:
            assert ident.startswith('System.Composition.'),(name,ident)
            E.SubElement(ig,'ProjectReference',Include=native(out/'baseline-net8'/ident/'Build.csproj'))
            dependencies[ident]='9.0.0'
        else:
            assert ident in names,(name,ident);dependencies[ident]='9.0.0'
    if bootstrap:
        E.SubElement(ig,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.9.2]')
    elif not baseline and not forwarder:
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
    records[name]=dict(configuration='Release',cls_compliant=cls=='true',original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),original_cs={p.relative_to(source).as_posix():sha(p) for p in selected},resource_files_sha256=extra_resources,
                       key=key,key_policy=key_policies[name]['policy'],original_package_minimums=original_packages,resolved_dependencies=dependencies,
                       original_supported_framework=tfm if not bootstrap else 'netstandard2.0',bootstrap_host_framework='net8.0' if bootstrap else None,production_cs_changes=0)
    if forwarder:
        assert not dependencies and not original_packages and not extra_resources
        assert set(records[name]['original_cs'])=={
            'src/libraries/Microsoft.Bcl.AsyncInterfaces/src/Microsoft.Bcl.AsyncInterfaces.Forwards.cs',
            'src/libraries/System.Private.CoreLib/src/System/Diagnostics/CodeAnalysis/NullableAttributes.cs'}
meta=E.Element('package');md=E.SubElement(meta,'metadata')
for k,v in dict(id='System.Composition',version='9.0.0',authors='.NET Foundation',description='Original source composition dependency metapackage.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/runtime',commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3')
deps=E.SubElement(md,'dependencies')
for tfm in ['.NETStandard2.0','net8.0']:
    group=E.SubElement(deps,'group',targetFramework=tfm)
    for n in names:
        if n.startswith('System.Composition.'):E.SubElement(group,'dependency',id=n,version='[9.0.0]')
save(meta,out/'System.Composition.nuspec')
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
for name,path in [('private',out/'feed'),('installed-source',Path('/clang64/lib/dotnet/library-packs'))]:E.SubElement(feeds,'add',key=name,value=native(path))
save(config,out/'NuGet.config');(out/'feed').mkdir()
(out/'source-inputs.json').write_text(json.dumps(dict(runtime_commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',source_root=native(source),projects=records,order=names,
    shared_sources_policy_sha256=sha(libs/'Directory.Build.targets'),generator_policy_sha256=sha(source/'eng/generators.targets'),composition_original_project_sha256=sha(libs/'System.Composition/src/System.Composition.csproj'),full_dependency_goal_complete=False),indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
print('Prepared original source9 graph', {n:len(r['original_cs']) for n,r in records.items()},flush=True)

(out/'tool-inputs.json').write_text(json.dumps({str(p):dict(owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip(),sha256=sha(p)) for p in [Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')/n for n in ['CompilerHost.dll','Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]},indent=2)+'\n')
