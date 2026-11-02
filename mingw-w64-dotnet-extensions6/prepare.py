"""Retarget the three complete original Extensions6 Core projects to source .NET8."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
gold={item['name']:item for item in json.loads((here/'published-metadata.json').read_text())}
provenance=json.loads((here/'published-provenance.json').read_text())
key=bytes.fromhex((here/'AspNetCore.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='adb9793829ddae60'
out.mkdir();libraries=source/'src/libraries'
sha=lambda data:hashlib.sha256(data).hexdigest()
records={}
for name in gold:
    target=out/name;target.mkdir()
    (target/'Library.public.snk').write_bytes(key)
    original=libraries/name/'src'/(name+'.csproj')
    tree=E.parse(original);upstream=tree.getroot();upstream.attrib.pop('Sdk')
    # Unsafe's actual implementation is supplied by the source .NET8 runtime.
    # Keep the other original dependency as a source project reference.
    framework_references=[]
    for parent in upstream.iter():
        for child in list(parent):
            if child.tag=='ProjectReference':
                include=child.get('Include')
                if 'System.Runtime.CompilerServices.Unsafe' in include:
                    framework_references.append(include);parent.remove(child)
                else:
                    assert 'Microsoft.Extensions.Primitives' in include,include
                    child.set('Include','../Microsoft.Extensions.Primitives/Library.csproj')
            elif child.tag=='Reference':
                # These legacy explicit names duplicate SDK targeting-pack refs.
                assert child.get('Include') in ['System.Runtime','System.Linq','System.Linq.Expressions','System.Collections']
                framework_references.append(child.get('Include'));parent.remove(child)
    E.indent(upstream);tree.write(target/'upstream.proj',encoding='utf-8',xml_declaration=True)
    rel=lambda p:os.path.relpath(p,target).replace('\\','/')
    project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
    for prop,value in dict(TargetFramework='net8.0',NetCoreAppCurrent='net8.0',
        TargetFrameworkIdentifier='.NETCoreApp',TargetOS='windows',TargetArchitecture='x64',
        CommonPath=rel(libraries/'Common/src')+'/',CoreLibSharedDir=rel(libraries/'System.Private.CoreLib/src')+'/',
        LibrariesProjectRoot=rel(libraries)+'/',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false').items():
        E.SubElement(props,prop).text=value
    E.SubElement(project,'Import',Project='upstream.proj')
    props=E.SubElement(project,'PropertyGroup')
    for prop,value in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,Version='6.0.0',
        AssemblyVersion=gold[name]['version'],FileVersion=gold[name]['attributes']['AssemblyFileVersionAttribute'],
        InformationalVersion=gold[name]['attributes']['AssemblyInformationalVersionAttribute'],
        IncludeSourceRevisionInInformationalVersion='false',RootNamespace=name,Nullable='annotations',
        EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',
        SignAssembly='true',PublicSign='true',DelaySign='false',AssemblyOriginatorKeyFile='Library.public.snk',
        GenerateDocumentationFile='true',NoWarn='CS1591',PackageLicenseExpression='MIT',
        PackageReadmeFile='README.md',RepositoryUrl='https://github.com/dotnet/runtime',RepositoryType='git',
        RepositoryCommit='4822e3c3aa77eb82b2fb33c9321f923cf11ddde6',ProduceReferenceAssembly='true').items():
        E.SubElement(props,prop).text=value
    if name=='Microsoft.Extensions.FileProviders.Abstractions':
        E.SubElement(props,'RootNamespace').text='Microsoft.Extensions.FileProviders'
    E.SubElement(props,'NuspecFile').text='Package.nuspec'
    E.SubElement(props,'NuspecBasePath').text='$(MSBuildProjectDirectory)'
    items=E.SubElement(project,'ItemGroup')
    original_cs=sorted(original.parent.rglob('*.cs'))
    for path in original_cs:E.SubElement(items,'Compile',Include=rel(path))
    E.SubElement(items,'Compile',Include=rel(libraries/'Common/src/System/SR.cs'))
    E.SubElement(items,'Compile',Include='SR.Generated.cs')
    resources=original.parent/'Resources/Strings.resx'
    values={item.get('name'):item.findtext('value') for item in E.parse(resources).iter('data')}
    assert len(gold[name]['resources'])==2
    for logical,expected in gold[name]['resources'].items():
        assert values==expected,(name,logical)
        E.SubElement(items,'EmbeddedResource',Include=rel(resources),LogicalName=logical,
                     ManifestResourceName=logical.removesuffix('.resources'))
    logical='FxResources.'+name+'.SR'
    lines=['namespace System { internal static partial class SR {',
           'private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(SR).Assembly);']
    for resource_name in values:
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',resource_name)
        lines.append('internal static string '+resource_name+' => GetResourceString('+json.dumps(resource_name)+');')
    lines.append('}}');(target/'SR.Generated.cs').write_text('\n'.join(lines)+'\n')
    record=dict(original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original.read_bytes()),
        original_cs={path.relative_to(source).as_posix():sha(path.read_bytes()) for path in original_cs},
        shared_cs={'src/libraries/Common/src/System/SR.cs':sha((libraries/'Common/src/System/SR.cs').read_bytes())},
        original_resources={resources.relative_to(source).as_posix():sha(resources.read_bytes())},
        expected_resource_sets=gold[name]['resources'],framework_provided_references=framework_references,
        production_cs_changes=[],generated_sr_sha256=sha((target/'SR.Generated.cs').read_bytes()),
        published_provenance=provenance[name])
    for child in upstream.iter('Compile'):
        include=child.get('Include','')
        if not include:continue
        path=include.replace('$(CoreLibSharedDir)',str(libraries/'System.Private.CoreLib/src')).replace('$(CommonPath)',str(libraries/'Common/src')+'/').replace('\\','/')
        if child.get('Condition'):
            assert "!= '.NETCoreApp'" in child.get('Condition');continue
        p=Path(path);assert p.is_file(),path
        record['shared_cs'][p.relative_to(source).as_posix()]=sha(p.read_bytes())
    (target/'source-inventory.json').write_text(json.dumps(record,indent=2)+'\n')
    for path,dest in [(source/'LICENSE.TXT','LICENSE.TXT'),(here/'README.md','README.md'),(target/'source-inventory.json','source-build/inventory.json')]:
        E.SubElement(items,'None',Include=rel(path),Pack='true',PackagePath=dest)
    E.SubElement(items,'None',Include='obj/Release/net8.0/ref/'+name+'.dll',Pack='true',PackagePath='ref/net8.0/'+name+'.dll')
    capture=E.SubElement(project,'Target',Name='RecordCompilerInputs',BeforeTargets='CoreCompile')
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)compiler-inputs.txt',
                 Lines="@(Compile->'%(FullPath)')",Overwrite='true')
    E.indent(project);E.ElementTree(project).write(target/'Library.csproj',encoding='utf-8',xml_declaration=True)
    # SDK pack does not emit explicit reference groups for manually supplied
    # ref assets; declare both the assets and their matching group explicitly.
    nuspec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
    meta=E.SubElement(nuspec,'metadata')
    for prop,value in dict(id=name,version='6.0.0',authors='Microsoft',
        description=upstream.findtext('PropertyGroup/PackageDescription').strip(),
        requireLicenseAcceptance='false',readme='README.md').items():E.SubElement(meta,prop).text=value
    E.SubElement(meta,'license',type='expression').text='MIT'
    E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/runtime',commit='4822e3c3aa77eb82b2fb33c9321f923cf11ddde6')
    group=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
    if name=='Microsoft.Extensions.FileProviders.Abstractions':E.SubElement(group,'dependency',id='Microsoft.Extensions.Primitives',version='6.0.0')
    reference=E.SubElement(E.SubElement(meta,'references'),'group',targetFramework='net8.0')
    E.SubElement(reference,'reference',file=name+'.dll')
    files=E.SubElement(nuspec,'files')
    for origin,destination in [(target/'bin/Release/net8.0'/(name+'.dll'),'lib/net8.0/'+name+'.dll'),
        (target/'bin/Release/net8.0'/(name+'.xml'),'lib/net8.0/'+name+'.xml'),
        (target/'obj/Release/net8.0/ref'/(name+'.dll'),'ref/net8.0/'+name+'.dll'),
        (source/'LICENSE.TXT','LICENSE.TXT'),(here/'README.md','README.md'),
        (target/'source-inventory.json','source-build/inventory.json')]:
        E.SubElement(files,'file',src=rel(origin),target=destination)
    E.indent(nuspec);E.ElementTree(nuspec).write(target/'Package.nuspec',encoding='utf-8',xml_declaration=True)
    records[name]=record
(out/'source-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
print('PASS full original Extensions6 source/resource inputs:',{name:len(item['original_cs'])+len(item['shared_cs']) for name,item in records.items()})
