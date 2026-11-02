"""Preserve original JSON .NET8 and three generator Compile/import conditions."""
from pathlib import Path
import hashlib,json,os,re,shutil,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
here=Path(__file__).resolve().parent;libraries=source/'src/libraries'
sha=lambda data:hashlib.sha256(data).hexdigest()
key=bytes.fromhex((here/'Open.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='cc7b13ffcd2ddd51'
baseline={}
for record in json.loads((here/'published-metadata.json').read_text()):
    path=record['file'].replace('\\','/').split('/metadata-only/')[1]
    assert record['public_key']==key.hex(),path
    baseline[path]=record
records={};localization=[]
for suffix in ['Lib','Gen3.11','Gen4.0','Gen4.4']:
    gen=suffix!='Lib';variant=suffix[3:] if gen else None
    target=out/suffix;target.mkdir();rel=lambda p:os.path.relpath(p,target).replace('\\','/')
    folder=libraries/'System.Text.Json'/('gen' if gen else 'src')
    original=folder/('System.Text.Json.SourceGeneration.Roslyn'+variant+'.csproj' if gen else 'System.Text.Json.csproj')
    name='System.Text.Json.SourceGeneration' if gen else 'System.Text.Json'
    asset='analyzers/dotnet/roslyn'+variant+'/cs/'+name+'.dll' if gen else 'lib/net8.0/'+name+'.dll'
    metadata=baseline[asset]
    (target/'Open.public.snk').write_bytes(key)
    upstream=E.parse(original);upstream.getroot().attrib.pop('Sdk')
    imports=[];candidates={};expected={};original_metadata={};framework_references=[]
    # The original conditions below are retained in imported build metadata.
    # Record their independently selected net8.0 Compile set as an audit gate.
    conditions={None:True,"'$(TargetFrameworkIdentifier)' != '.NETCoreApp'":False,
        "'$(TargetFrameworkIdentifier)' == '.NETCoreApp'":True,
        "'$(TargetFrameworkIdentifier)' == '.NETCoreApp' and $([MSBuild]::VersionGreaterThanOrEquals('$(TargetFrameworkVersion)', '7.0'))":True,
        "!$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net7.0'))":False,
        "!$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net8.0'))":False,
        "$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net8.0'))":True}
    def rewrite(tree,original_file):
        original_metadata[original_file.relative_to(source).as_posix()]=sha(original_file.read_bytes())
        for group in tree.getroot():
            for item in list(group):
                if item.tag=='Reference':
                    assert not gen and item.get('Include').startswith('System.'),item.attrib
                    framework_references.append(item.get('Include'));group.remove(item);continue
                if item.tag=='Compile' and item.get('Include'):
                    value=item.get('Include').replace('$(CommonPath)',str(libraries/'Common/src')+'/').replace('$(CoreLibSharedDir)',str(libraries/'System.Private.CoreLib/src')+'/').replace('\\','/')
                    path=(original_file.parent/value).resolve();assert path.is_file(),path
                    relative=path.relative_to(source).as_posix();candidates[relative]=sha(path.read_bytes())
                    assert item.get('Condition') is None,item.attrib
                    assert group.get('Condition') in conditions,group.get('Condition')
                    if conditions[group.get('Condition')]:expected[relative]=candidates[relative]
                if item.tag in ['Compile','EmbeddedResource','None','Content']:
                    for attr in ['Include','Remove','Update']:
                        value=item.get(attr)
                        if value and not value.startswith('$('):item.set(attr,rel((original_file.parent/value.replace('\\','/')).resolve()))
                if item.tag=='PackageReference':
                    assert item.get('Include')=='Microsoft.CodeAnalysis.CSharp.Workspaces' or not gen,item.attrib
                    if gen:item.set('Version','[4.9.2]')
                if item.tag=='ProjectReference':
                    value=item.get('Include')
                    if 'System.Text.Json.SourceGeneration.Roslyn' in value:
                        v=re.search(r'Roslyn(3\.11|4\.0|4\.4)',value)[1]
                        item.set('Include','../Gen'+v+'/Library.csproj')
            if group.tag=='Import':
                imported=(original_file.parent/group.get('Project')).resolve()
                assert imported.name=='System.Text.Json.SourceGeneration.targets',imported
                shared=E.parse(imported);rewrite(shared,imported)
                E.indent(shared);shared.write(target/'upstream.targets',encoding='utf-8',xml_declaration=True)
                group.set('Project','upstream.targets');imports.append(imported.relative_to(source).as_posix())
    rewrite(upstream,original)
    E.indent(upstream);upstream.write(target/'upstream.proj',encoding='utf-8',xml_declaration=True)
    project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
    for prop,value in dict(TargetFramework='net8.0',NetCoreAppCurrent='net8.0',NetCoreAppPrevious='net7.0',
        NetCoreAppMinimum='net6.0',NetCoreAppToolCurrent='net8.0',NetFrameworkMinimum='net462',
        TargetFrameworkIdentifier='.NETCoreApp',TargetOS='windows',TargetArchitecture='x64',
        CommonPath=rel(libraries/'Common/src')+'/',CoreLibSharedDir=rel(libraries/'System.Private.CoreLib/src')+'/',
        LibrariesProjectRoot=rel(libraries)+'/',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',
        EnableDefaultItems='false',DotNetBuildFromSource='false').items():E.SubElement(props,prop).text=value
    E.SubElement(project,'Import',Project='upstream.proj')
    props=E.SubElement(project,'PropertyGroup')
    for prop,value in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,RootNamespace=name,
        Version='8.0.5',AssemblyVersion=metadata['version'],FileVersion=metadata['attributes']['AssemblyFileVersionAttribute'],
        InformationalVersion=metadata['attributes']['AssemblyInformationalVersionAttribute'],
        IncludeSourceRevisionInInformationalVersion='false',Nullable='enable',LangVersion='12.0',
        EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',GeneratePackageOnBuild='false',
        SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='Open.public.snk',
        GenerateDocumentationFile='true',NoWarn='$(NoWarn);CS1591;CS0436',TreatWarningsAsErrors='false',
        StringResourcesName='FxResources.'+name+'.SR',ProduceReferenceAssembly='true').items():E.SubElement(props,prop).text=value
    items=E.SubElement(project,'ItemGroup')
    attribute=E.SubElement(items,'AssemblyAttribute',Include='System.CLSCompliantAttribute')
    E.SubElement(attribute,'_Parameter1').text='false' if gen else 'true'
    for prop,value in [('Company','Microsoft Corporation'),('Product','Microsoft® .NET'),('Title',name)]:
        E.SubElement(props,prop).text=value
    if not gen:
        attribute=E.SubElement(items,'AssemblyAttribute',Include='System.Resources.NeutralResourcesLanguageAttribute')
        E.SubElement(attribute,'_Parameter1').text='en-US'
        attribute=E.SubElement(items,'AssemblyAttribute',Include='System.Reflection.AssemblyMetadataAttribute')
        E.SubElement(attribute,'_Parameter1').text='IsTrimmable'
        E.SubElement(attribute,'_Parameter2').text='True'
    sr=libraries/'Common/src/System/SR.cs';expected[sr.relative_to(source).as_posix()]=sha(sr.read_bytes())
    E.SubElement(items,'Compile',Include=rel(sr));E.SubElement(items,'Compile',Include='SR.Generated.cs')
    resources=folder/'Resources/Strings.resx';logical='FxResources.'+name+'.SR'
    values={e.get('name'):(e.findtext('value') or '').replace('\r\n','\n').replace('\n','\r\n') for e in E.parse(resources).iter('data')}
    assert metadata['resources']=={logical+'.resources':values},(suffix,'neutral resources')
    code=['#nullable enable','namespace System { internal static partial class SR {',
          'internal static System.Resources.ResourceManager ResourceManager { get; } = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(SR).Assembly);']
    for field in values:
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',field),field
        code.append('internal static string '+field+' => GetResourceString('+json.dumps(field)+');')
    code+=['}}','namespace '+logical.rpartition('.')[0]+' { internal static class SR {} }']
    (target/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
    resource_sources={resources.relative_to(source).as_posix():sha(resources.read_bytes())}
    if not gen:
        descriptor=folder/'ILLink/ILLink.Substitutions.xml'
        template=source/'eng/ILLink.Substitutions.Resources.template'
        combined=E.parse(descriptor).getroot()
        extra=E.fromstring(template.read_text().replace('{AssemblyName}',name).replace('{StringResourcesName}',logical))
        for child in extra:combined.append(child)
        (target/'ILLink.Substitutions.xml').write_bytes(E.tostring(combined,encoding='utf-8',xml_declaration=True))
        E.SubElement(items,'EmbeddedResource',Include='ILLink.Substitutions.xml',LogicalName='ILLink.Substitutions.xml')
        for path in [descriptor,template]:resource_sources[path.relative_to(source).as_posix()]=sha(path.read_bytes())
    def write_resource(path,culture,strings):
        tree=E.parse(resources)
        for e in tree.iter('data'):e.find('value').text=strings[e.get('name')]
        path.write_bytes(E.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True).replace(b'\r',b'&#13;'))
        manifest=logical+('.'+culture if culture else '')+'.resources'
        attrs=dict(Include=path.name,LogicalName=manifest)
        if culture:attrs.update(Culture=culture,WithCulture='true')
        E.SubElement(items,'EmbeddedResource',**attrs)
        localization.append(dict(project=suffix,culture=culture,manifest=manifest,strings=strings,prepared_sha256=sha(path.read_bytes())))
    write_resource(target/'Strings.resx','',values)
    if gen:
        for translation in sorted((resources.parent/'xlf').glob('Strings.*.xlf')):
            tree=E.parse(translation);ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
            culture=tree.find('x:file',ns).get('target-language')
            translated=dict(values)
            for e in tree.findall('.//x:trans-unit',ns):
                t=e.find('x:target',ns)
                if t is not None and e.get('id') in translated:
                    translated[e.get('id')]=''.join(t.itertext()).replace('\r\n','\n').replace('\n','\r\n')
            published=baseline[asset.rsplit('/',1)[0]+'/'+culture+'/'+name+'.resources.dll']
            assert published['resources']=={logical+'.'+culture+'.resources':translated},(suffix,culture)
            write_resource(target/('Strings.'+culture+'.resx'),culture,translated)
            resource_sources[translation.relative_to(source).as_posix()]=sha(translation.read_bytes())
    # Match the runtime repository's reference exclusions for self/shared JSON
    # sources while retaining actual framework implementations for other BCL APIs.
    remove=E.SubElement(project,'Target',Name='ExcludeOriginalJsonFrameworkReference',AfterTargets='ResolveTargetingPackAssets')
    E.SubElement(E.SubElement(remove,'ItemGroup'),'Reference',Remove='@(Reference)',Condition="'%(FileName)' == 'System.Text.Json'")
    capture=E.SubElement(project,'Target',Name='RecordActualCompilerInputs',BeforeTargets='CoreCompile')
    for kind,filename in [('Compile','compiler-inputs.txt'),('ReferencePath','reference-inputs.txt')]:
        E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+filename,Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
    E.indent(project);E.ElementTree(project).write(target/'Library.csproj',encoding='utf-8',xml_declaration=True)
    records[suffix]=dict(assembly=name,variant=variant,published_asset=asset,original_project_metadata=original_metadata,
        declared_original_cs_candidates=candidates,expected_original_compile_items=expected,original_resource_sources=resource_sources,
        generated_sr_sha256=sha((target/'SR.Generated.cs').read_bytes()),framework_provided_references=framework_references,
        production_cs_changes=[])
(out/'source-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localization,ensure_ascii=False,indent=2)+'\n')
feed='E:/msys64/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
print('PASS complete original JSON/generator imports and selected compiler items:',{k:len(v['expected_original_compile_items']) for k,v in records.items()})
