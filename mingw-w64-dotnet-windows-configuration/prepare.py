"""Adapt the selected upstream .NET 8 projects to the installed offline SDK.

Keep upstream conditional Compile items so MSBuild selects the actual Windows
implementations. No upstream binary files or NuGet implementations are used.
"""
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import xml.etree.ElementTree as E

source, winforms, output, installed_feed = map(Path, sys.argv[1:])
source,winforms=source.resolve(),winforms.resolve()
output.mkdir()
inputs = Path(__file__).resolve().parent
libraries = json.loads((inputs / 'libraries.json').read_text())
removed = []
for f in sorted(source.rglob('*')):
    if f.is_file() and f.suffix.lower() in {'.dll', '.exe', '.nupkg', '.pdb', '.so', '.dylib', '.a', '.lib', '.winmd', '.res'}:
        removed.append(str(f.relative_to(source)))
        f.unlink()
(output / 'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
for f in sorted(winforms.rglob('*')):
    if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.winmd','.res'}:
        removed.append('winforms/'+str(f.relative_to(winforms)))
        f.unlink()
(output / 'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
for library in libraries:
    drawing=library.get('source')=='winforms'
    root = winforms/'src' if drawing else source/'src/libraries'
    name, version, framework = (library[k] for k in ('id', 'version', 'framework'))
    original = root / name / 'src' / (name+'.csproj')
    upstream = E.parse(original).getroot()
    servicing = upstream.findtext('./PropertyGroup/ServicingVersion') or '0'
    assert version == ('8.0.31' if drawing else '8.0.'+servicing), (name, version, servicing)
    key_id = 'Open' if drawing else E.parse(root/name/'Directory.Build.props').findtext('./PropertyGroup/StrongNameKeyId') or 'Open'
    assert key_id == library['key'], (name,key_id)
    for imp in upstream.findall('Import'):
        assert drawing and imp.get('Project') in {'resources.targets','packaging.targets'}, imp.attrib
        upstream.remove(imp)
    project_dir = output / name
    project_dir.mkdir()
    def relative(path):
        return os.path.relpath(path, project_dir).replace('\\', '/')
    upstream.attrib.pop('Sdk', None)
    for group in upstream.findall('PropertyGroup'):
        for element in list(group):
            if element.tag in {'TargetFrameworks','TargetFramework'}:
                group.remove(element)
    # Relative items in imported MSBuild files are relative to the main project.
    # Anchor every such source path to the original project directory.
    for group in upstream.findall('ItemGroup'):
        for element in group:
            if element.tag not in {'Compile', 'EmbeddedResource', 'ProjectReference', 'None', 'Content'}:
                continue
            for attribute in ('Include', 'Remove', 'Update'):
                if element.tag=='EmbeddedResource' and not element.get('LogicalName'):
                    element.set('LogicalName',name+'.'+element.get('Include','').replace('\\','.').replace('/','.'))
                value = element.get(attribute)
                if value and not value.startswith('$('):
                    element.set(attribute, (relative(original.parent)+'/'+value).replace('\\','/'))
    (project_dir/'Library.public.snk').write_bytes(bytes.fromhex((inputs/(key_id+'.pubkey.hex')).read_text()))
    for group in upstream.findall('ItemGroup'):
        # Replace project dependencies with separately packed source libraries.
        for item in list(group):
            if item.tag in {'ProjectReference','PackageReference'}:
                group.remove(item)
    E.indent(upstream)
    E.ElementTree(upstream).write(project_dir/'upstream.proj', encoding='utf-8', xml_declaration=True)
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = E.SubElement(project,'PropertyGroup')
    values = {
        'TargetFramework':framework, 'NetCoreAppCurrent':'net8.0', 'NetCoreAppPrevious':'net7.0',
        'NetCoreAppMinimum':'net6.0', 'NetCurrent':'net8.0','NetPrevious':'net7.0','NetMinimum':'net6.0', 'RepoRoot':relative(winforms)+'/', 'DefaultLanguageSourceExtension':'.cs', 'NetFrameworkMinimum':'net462', 'TargetFrameworkIdentifier':'.NETCoreApp',
        'TargetOS':'windows', 'TargetsWindows':'true', 'TargetArchitecture':'x64',
        'CommonPath':relative(root)+'/Common/src/', 'LibrariesProjectRoot':relative(root)+'/',
        'CoreLibSharedDir':relative(root)+'/System.Private.CoreLib/src/',
        'EnableDefaultCompileItems':'false', 'EnableDefaultEmbeddedResourceItems':'false',
        'EnableDefaultNoneItems':'false', 'ImportDirectoryBuildProps':'false', 'ImportDirectoryBuildTargets':'false',
        'AssemblyName':name, 'RootNamespace':name, 'Version':version, 'AssemblyVersion':'8.0.0.0',
        'InformationalVersion':version+('+'+'winforms' if drawing else '+runtime')+'-v8.0.31', 'Nullable':'enable',
        'AllowUnsafeBlocks':'true', 'SignAssembly':'true', 'PublicSign':'true',
        'AssemblyOriginatorKeyFile':'Library.public.snk', 'EnableNETAnalyzers':'false', 'NuGetAudit':'false',
        'NoWarn':'CS0436;CS0618;SYSLIB0051;SYSLIB0003', 'IsPackable':'true', 'PackageLicenseExpression':'MIT',
        'RepositoryUrl':'https://github.com/dotnet/'+('winforms' if drawing else 'runtime'), 'RepositoryType':'git',
    }
    for key,value in values.items(): E.SubElement(props,key).text=value
    E.SubElement(project,'Import', Project='upstream.proj')
    items=E.SubElement(project,'ItemGroup')
    for dep,dep_version in library['dependencies'].items():
        E.SubElement(items,'PackageReference',Include=dep,Version='['+dep_version+']')
    if upstream.findtext('./PropertyGroup/IsPartialFacadeAssembly')=='true':
        for forwards in (root/name/'ref').glob('*.Forwards.cs'):
            E.SubElement(items,'Compile',Include=relative(forwards))
    resources=original.parent/'Resources/Strings.resx'
    assert resources.is_file(), name
    logical='FxResources.'+name+'.SR'
    E.SubElement(items,'Compile',Include=relative(winforms/'src/Common/src/SR.cs' if drawing else root/'Common/src/System/SR.cs'))
    E.SubElement(items,'Compile',Include='SR.Generated.cs')
    E.SubElement(items,'EmbeddedResource',Include=relative(resources),LogicalName=logical+'.resources')
    lines=['namespace System { internal static partial class SR {', 'private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(SR).Assembly);']
    for data in E.parse(resources).iter('data'):
        key=data.get('name')
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key),key
        lines.append('internal static string '+key+' => GetResourceString('+json.dumps(key)+');')
    lines.append('}}')
    (project_dir/'SR.Generated.cs').write_text('\n'.join(lines)+'\n')
    # PowerShell targets plain net8.0. Expose the upstream net8.0 contract
    # and use RID-selected Windows implementations, as upstream NuGet does.
    if framework.endswith('-windows') or library.get('platform_specific'):
        E.SubElement(props,'NuspecFile').text='Package.nuspec'
        E.SubElement(props,'NuspecBasePath').text='$(MSBuildThisFileDirectory)'
    contract_dir=project_dir/'contract'
    contract_dir.mkdir()
    contract=E.Element('Project',Sdk='Microsoft.NET.Sdk')
    cp=E.SubElement(contract,'PropertyGroup')
    for key,value in {
        'TargetFramework':'net8.0', 'AssemblyName':name, 'AssemblyVersion':'8.0.0.0',
        'EnableDefaultCompileItems':'false', 'EnableNETAnalyzers':'false', 'NuGetAudit':'false',
        'Nullable':'annotations', 'ProduceReferenceAssembly':'true',
        'SignAssembly':'true', 'PublicSign':'true', 'AssemblyOriginatorKeyFile':'../Library.public.snk',
        'NoWarn':'CS0108;CS0067;CS0672;CS0809;CS3021;SYSLIB0003;SYSLIB0051',
    }.items(): E.SubElement(cp,key).text=value
    ci=E.SubElement(contract,'ItemGroup')
    for dep,dep_version in library['dependencies'].items():
        E.SubElement(ci,'PackageReference',Include=dep,Version='['+dep_version+']')
    if drawing:
        contract_source=(original.parent/'NotSupported.cs').read_text(encoding='utf-8-sig')
        # These two types moved into Drawing.Primitives on .NET Core.
        # Keep their upstream forwards instead of the .NET Standard definitions.
        for moved in ('ColorTranslator','SystemColors'):
            contract_source,count=re.subn(r'(?ms)^    public static partial class '+moved+r'\n    \{.*?^    \}\n','',contract_source)
            assert count==1, moved
        (contract_dir/'Drawing.Contract.cs').write_text(contract_source)
        E.SubElement(ci,'Compile',Include='Drawing.Contract.cs')
        E.SubElement(ci,'Compile',Include=os.path.relpath(original.parent/'Forwards.cs',contract_dir).replace('\\','/'))
        (contract_dir/'SR.Contract.cs').write_text('namespace System { internal static class SR { internal const string SystemDrawingCommon_PlatformNotSupported = "Reference contract"; }}')
        E.SubElement(ci,'Compile',Include='SR.Contract.cs')
    else:
        ref_project=E.parse(root/name/'ref'/(name+'.csproj')).getroot()
        ref_items=E.SubElement(contract,'ItemGroup')
        for group in ref_project.findall('ItemGroup'):
            for item in group.findall('Compile'):
                include=item.get('Include')
                assert include, name
                if '$(' in include:
                    assert include.startswith('$(CommonPath)'), (name,include)
                    ref_source=source/'src/libraries/Common/src'/include[len('$(CommonPath)'):].replace('\\','/')
                else:
                    ref_source=root/name/'ref'/include.replace('\\','/')
                clone=E.fromstring(E.tostring(item))
                clone.set('Include',os.path.relpath(ref_source,contract_dir).replace('\\','/'))
                if group.get('Condition'):
                    clone.set('Condition','('+group.get('Condition')+') and ('+(clone.get('Condition') or 'true')+')')
                ref_items.append(clone)
        for k,v in {'NetCoreAppCurrent':'net8.0','NetCoreAppPrevious':'net7.0','NetCoreAppMinimum':'net6.0','NetFrameworkMinimum':'net462'}.items():E.SubElement(cp,k).text=v
    E.indent(contract)
    E.ElementTree(contract).write(contract_dir/'Contract.csproj',encoding='utf-8',xml_declaration=True)
    nuspec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
    metadata=E.SubElement(nuspec,'metadata')
    for key,value in {'id':name,'version':version,'authors':'Microsoft','description':upstream.findtext('./PropertyGroup/PackageDescription') or name}.items():
        E.SubElement(metadata,key).text=value
    E.SubElement(metadata,'license',type='expression').text='MIT'
    E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/'+('winforms' if drawing else 'runtime'),branch='v8.0.31')
    dependencies=E.SubElement(metadata,'dependencies')
    dependency_group=E.SubElement(dependencies,'group',targetFramework='net8.0')
    for dep,dep_version in library['dependencies'].items():
        E.SubElement(dependency_group,'dependency',id=dep,version='['+dep_version+']')
    files=E.SubElement(nuspec,'files')
    E.SubElement(files,'file',src='bin/Release/'+framework+'/'+name+'.dll',target='runtimes/win/lib/net8.0/')
    E.SubElement(files,'file',src='contract/obj/Release/net8.0/ref/'+name+'.dll',target='ref/net8.0/')
    if name=='System.Diagnostics.EventLog':
        E.SubElement(files,'file',src='messages/bin/Release/net8.0/System.Diagnostics.EventLog.Messages.dll',target='runtimes/win/lib/net8.0/')
    E.indent(nuspec)
    E.ElementTree(nuspec).write(project_dir/'Package.nuspec',encoding='utf-8',xml_declaration=True)
    E.indent(project)
    E.ElementTree(project).write(project_dir/'Library.csproj',encoding='utf-8',xml_declaration=True)
def native(path):
    return subprocess.check_output(['cygpath','-am',str(path)],text=True).strip() if sys.platform.startswith(('cygwin','msys')) else str(path.resolve())
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
E.SubElement(feeds,'add',key='private-source-built',value=native(output.parent/'feed'))
E.SubElement(feeds,'add',key='installed-source-built',value=native(installed_feed))
E.indent(config);E.ElementTree(config).write(output/'NuGet.config',encoding='utf-8',xml_declaration=True)

