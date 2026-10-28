"""Adapt the selected upstream .NET 8 projects to the installed offline SDK.

Keep upstream conditional Compile items so MSBuild selects the actual Windows
implementations. No upstream binary files or NuGet implementations are used.
"""
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as E

source, output = map(Path, sys.argv[1:])
source = source.resolve()
output.mkdir()
inputs = Path(__file__).resolve().parent
libraries = json.loads((inputs / 'libraries.json').read_text())
removed = []
for f in sorted(source.rglob('*')):
    if f.is_file() and f.suffix.lower() in {'.dll', '.exe', '.nupkg', '.pdb', '.so', '.dylib', '.a', '.lib', '.winmd'}:
        removed.append(str(f.relative_to(source)))
        f.unlink()
(output / 'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
root = source / 'src/libraries'
for library in libraries:
    name, version, framework = (library[k] for k in ('id', 'version', 'framework'))
    original = root / name / 'src' / (name+'.csproj')
    upstream = E.parse(original).getroot()
    servicing = upstream.findtext('./PropertyGroup/ServicingVersion') or '0'
    assert version == '8.0.'+servicing, (name, version, servicing)
    key_id = E.parse(root / name / 'Directory.Build.props').findtext('./PropertyGroup/StrongNameKeyId')
    assert key_id == 'Microsoft', (name, key_id)
    assert not upstream.findall('Import'), 'Handle upstream imports explicitly before adding projects'
    project_dir = output / name
    project_dir.mkdir()
    def relative(path):
        return os.path.relpath(path, project_dir).replace('\\', '/')
    upstream.attrib.pop('Sdk', None)
    for group in upstream.findall('PropertyGroup'):
        for element in list(group):
            if element.tag == 'TargetFrameworks':
                group.remove(element)
    # Relative items in imported MSBuild files are relative to the main project.
    # Anchor every such source path to the original project directory.
    for group in upstream.findall('ItemGroup'):
        for element in group:
            if element.tag not in {'Compile', 'EmbeddedResource', 'ProjectReference', 'None', 'Content'}:
                continue
            for attribute in ('Include', 'Remove', 'Update'):
                value = element.get(attribute)
                if value and not value.startswith('$('):
                    element.set(attribute, (relative(original.parent)+'/'+value).replace('\\','/'))
    E.indent(upstream)
    E.ElementTree(upstream).write(project_dir/'upstream.proj', encoding='utf-8', xml_declaration=True)
    (project_dir/'Microsoft.public.snk').write_bytes(bytes.fromhex((inputs/'Microsoft.pubkey.hex').read_text()))
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = E.SubElement(project,'PropertyGroup')
    values = {
        'TargetFramework':framework, 'NetCoreAppCurrent':'net8.0', 'NetCoreAppPrevious':'net7.0',
        'NetCoreAppMinimum':'net6.0', 'NetFrameworkMinimum':'net462', 'TargetFrameworkIdentifier':'.NETCoreApp',
        'TargetOS':'windows', 'TargetsWindows':'true', 'TargetArchitecture':'x64',
        'CommonPath':relative(root)+'/Common/src/', 'LibrariesProjectRoot':relative(root)+'/',
        'CoreLibSharedDir':relative(root)+'/System.Private.CoreLib/src/',
        'EnableDefaultCompileItems':'false', 'EnableDefaultEmbeddedResourceItems':'false',
        'EnableDefaultNoneItems':'false', 'ImportDirectoryBuildProps':'false', 'ImportDirectoryBuildTargets':'false',
        'AssemblyName':name, 'RootNamespace':name, 'Version':version, 'AssemblyVersion':'8.0.0.0',
        'InformationalVersion':version+'+runtime-v8.0.31', 'Nullable':'enable',
        'AllowUnsafeBlocks':'true', 'SignAssembly':'true', 'PublicSign':'true',
        'AssemblyOriginatorKeyFile':'Microsoft.public.snk', 'EnableNETAnalyzers':'false', 'NuGetAudit':'false',
        'NoWarn':'CS0436;SYSLIB0051;SYSLIB0003', 'IsPackable':'true', 'PackageLicenseExpression':'MIT',
        'RepositoryUrl':'https://github.com/dotnet/runtime', 'RepositoryType':'git',
    }
    for key,value in values.items(): E.SubElement(props,key).text=value
    E.SubElement(project,'Import', Project='upstream.proj')
    items=E.SubElement(project,'ItemGroup')
    resources=original.parent/'Resources/Strings.resx'
    assert resources.is_file(), name
    logical='FxResources.'+name+'.SR'
    E.SubElement(items,'Compile',Include=relative(root/'Common/src/System/SR.cs'))
    E.SubElement(items,'Compile',Include='SR.Generated.cs')
    E.SubElement(items,'EmbeddedResource',Include=relative(resources),LogicalName=logical+'.resources')
    lines=['namespace System { internal static partial class SR {', 'private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(SR).Assembly);']
    for data in E.parse(resources).iter('data'):
        key=data.get('name')
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key),key
        lines.append('internal static string '+key+' => GetResourceString('+json.dumps(key)+');')
    lines.append('}}')
    (project_dir/'SR.Generated.cs').write_text('\n'.join(lines)+'\n')
    if framework.endswith('-windows'):
        # PowerShell targets plain net8.0. Expose the upstream net8.0 contract
        # and use RID-selected Windows implementations, as upstream NuGet does.
        E.SubElement(props,'NuspecFile').text='Package.nuspec'
        E.SubElement(props,'NuspecBasePath').text='$(MSBuildThisFileDirectory)'
        contract_dir=project_dir/'contract'
        contract_dir.mkdir()
        contract=E.Element('Project',Sdk='Microsoft.NET.Sdk')
        cp=E.SubElement(contract,'PropertyGroup')
        for key,value in {
            'TargetFramework':'net8.0', 'AssemblyName':name, 'AssemblyVersion':'8.0.0.0',
            'EnableDefaultCompileItems':'false', 'EnableNETAnalyzers':'false', 'NuGetAudit':'false',
            'Nullable':'annotations', 'ProduceOnlyReferenceAssembly':'true',
            'SignAssembly':'true', 'PublicSign':'true', 'AssemblyOriginatorKeyFile':'../Microsoft.public.snk',
            'NoWarn':'CS0108;CS0067;CS0809;CS3021;SYSLIB0003;SYSLIB0051',
        }.items(): E.SubElement(cp,key).text=value
        ci=E.SubElement(contract,'ItemGroup')
        E.SubElement(ci,'Compile',Include=os.path.relpath(root/name/'ref'/(name+'.cs'),contract_dir).replace('\\','/'))
        E.indent(contract)
        E.ElementTree(contract).write(contract_dir/'Contract.csproj',encoding='utf-8',xml_declaration=True)
        nuspec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
        metadata=E.SubElement(nuspec,'metadata')
        for key,value in {'id':name,'version':version,'authors':'Microsoft','description':upstream.findtext('./PropertyGroup/PackageDescription') or name}.items():
            E.SubElement(metadata,key).text=value
        E.SubElement(metadata,'license',type='expression').text='MIT'
        E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/runtime',branch='v8.0.31')
        dependencies=E.SubElement(metadata,'dependencies')
        E.SubElement(dependencies,'group',targetFramework='net8.0')
        files=E.SubElement(nuspec,'files')
        E.SubElement(files,'file',src='bin/Release/'+framework+'/'+name+'.dll',target='runtimes/win/lib/net8.0/')
        E.SubElement(files,'file',src='contract/bin/Release/net8.0/'+name+'.dll',target='ref/net8.0/')
        E.indent(nuspec)
        E.ElementTree(nuspec).write(project_dir/'Package.nuspec',encoding='utf-8',xml_declaration=True)
    E.indent(project)
    E.ElementTree(project).write(project_dir/'Library.csproj',encoding='utf-8',xml_declaration=True)
(output/'NuGet.config').write_text('<configuration><packageSources><clear /></packageSources></configuration>\n')
