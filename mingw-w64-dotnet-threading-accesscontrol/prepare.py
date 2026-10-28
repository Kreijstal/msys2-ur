"""Stage the missing Windows compatibility libraries from pinned runtime sources."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as E

source, output = (Path(x).resolve() for x in sys.argv[1:])
output.mkdir()
inputs = Path(__file__).resolve().parent
libraries = json.loads((inputs/'libraries.json').read_text())
removed=[]
for f in source.rglob('*'):
    if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.so','.a','.lib','.winmd','.res'}:
        removed.append(str(f.relative_to(source)));f.unlink()
(output/'removed-binaries.json').write_text(json.dumps(sorted(removed),indent=2)+'\n')
# Normalize source paths before passing them to MSBuild. Its resource task can
# reject an unnormalized path longer than MAX_PATH even when the resolved path
# exists and is shorter. Convert the root only, preserving wildcard characters.
source_native=subprocess.check_output(['cygpath','-am',str(source)],text=True).strip() if sys.platform.startswith(('cygwin','msys')) else str(source)
def source_path(path):
    return source_native+'/'+Path(path).resolve().relative_to(source).as_posix()
root=source/'src/libraries'
localizations=[]

for library in libraries:
    name,version,framework=(library[k] for k in ('id','version','framework'))
    original=root/name/'src'/(name+'.csproj')
    upstream=E.parse(original).getroot()
    servicing=upstream.findtext('./PropertyGroup/ServicingVersion') or '0'
    assert version=='8.0.'+servicing,(name,version,servicing)
    key_props=root/name/'Directory.Build.props'
    key=(E.parse(key_props).findtext('./PropertyGroup/StrongNameKeyId') if key_props.exists() else None) or 'Open'
    assert key==library['key'],(name,key)
    folder=output/name;folder.mkdir()
    def relative(p,base=folder): return source_path(p)
    upstream.attrib.pop('Sdk',None)
    for group in upstream.findall('PropertyGroup'):
        for prop in list(group):
            if prop.tag in {'TargetFramework','TargetFrameworks'}:group.remove(prop)
    for imp in upstream.findall('Import'):
        path=imp.get('Project')
        assert name=='System.Security.Cryptography.Pkcs' and path in {
            '$(CommonPath)System\\Security\\Cryptography\\Asn1\\AsnXml.targets',
            '$(CommonPath)System\\Security\\Cryptography\\Asn1Reader\\System.Security.Cryptography.Asn1Reader.Shared.projitems'},(name,path)
        # Keep upstream XML->C# generation and the shared ASN reader items.
    for group in upstream.findall('ItemGroup'):
        for item in list(group):
            if item.tag in {'ProjectReference','PackageReference','Reference'}:
                group.remove(item);continue
            if item.tag not in {'Compile','AsnXml','None','Content','EmbeddedResource'}:continue
            for attr in ('Include','Remove','Update'):
                value=item.get(attr)
                if value and not value.startswith('$(') and not value.startswith('@('):
                    item.set(attr,source_path(original.parent/value.replace('\\','/')))
    E.indent(upstream);E.ElementTree(upstream).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
    (folder/'Library.public.snk').write_bytes(bytes.fromhex((inputs/(key+'.pubkey.hex')).read_text()))
    p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
    values={
        'TargetFramework':framework,'TargetFrameworkIdentifier':'.NETCoreApp','NetCoreAppCurrent':'net8.0',
        'NetCoreAppPrevious':'net7.0','NetCoreAppMinimum':'net6.0','NetFrameworkMinimum':'net462',
        'NetCurrent':'net8.0','NetPrevious':'net7.0','NetMinimum':'net6.0',
        'TargetOS':'windows','TargetsWindows':'true','TargetArchitecture':'x64',
        'CommonPath':relative(root/'Common/src')+'/', 'LibrariesProjectRoot':relative(root)+'/',
        'CoreLibSharedDir':relative(root/'System.Private.CoreLib/src')+'/',
        'EnableDefaultCompileItems':'false','EnableDefaultEmbeddedResourceItems':'false','EnableDefaultNoneItems':'false',
        'AssemblyName':name,'RootNamespace':name,'Version':version,'AssemblyVersion':'8.0.0.0',
        # Identify the actual servicing source release and outrank the bootstrap's
        # older inbox files when NuGet/host resolve assemblies with identical identities.
        'FileVersion':'8.0.31.0','InformationalVersion':version+'+runtime-v8.0.31',
        'AllowUnsafeBlocks':'true','Nullable':'enable','SignAssembly':'true','PublicSign':'true',
        'AssemblyOriginatorKeyFile':'Library.public.snk','EnableNETAnalyzers':'false','NuGetAudit':'false',
        'NoWarn':'CS0436;CS0618;SYSLIB0003;SYSLIB0051','PackageLicenseExpression':'MIT',
        'RepositoryUrl':'https://github.com/dotnet/runtime','RepositoryType':'git',
        'ImportDirectoryBuildProps':'false','ImportDirectoryBuildTargets':'false',
    }
    for k,v in values.items():E.SubElement(props,k).text=v
    E.SubElement(p,'Import',Project='upstream.proj')
    items=E.SubElement(p,'ItemGroup')
    for dep,ver in library['dependencies'].items():E.SubElement(items,'PackageReference',Include=dep,Version='['+ver+']')
    res=original.parent/'Resources/Strings.resx';assert res.is_file(),name
    logical='ExceptionStringTable' if name=='System.Speech' else 'FxResources.'+name+'.SR'
    if name!='System.Speech':
        E.SubElement(items,'Compile',Include=relative(root/'Common/src/System/SR.cs'))
        E.SubElement(items,'Compile',Include='SR.Generated.cs')
        E.SubElement(items,'EmbeddedResource',Include=relative(res),LogicalName=logical+'.resources')
    else:
        resource=next(e for e in upstream.iter('EmbeddedResource') if e.get('ManifestResourceName')=='ExceptionStringTable')
        resource.set('LogicalName','ExceptionStringTable.resources')
        E.indent(upstream);E.ElementTree(upstream).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
    code=['namespace System { internal static partial class SR {',
          'private static readonly System.Resources.ResourceManager ResourceManager=new System.Resources.ResourceManager('+json.dumps(logical)+',typeof(SR).Assembly);']
    for data in E.parse(res).iter('data'):
        key_name=data.get('name');assert key_name.isidentifier(),key_name
        code.append('internal static string '+key_name+' => GetResourceString('+json.dumps(key_name)+');')
    code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
    localizations.append({'assembly':name,'resource':logical,'culture':'','strings':{d.get('name'):d.find('value').text or '' for d in E.parse(res).iter('data')}})
    ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
    for translation in sorted((res.parent/'xlf').glob(res.stem+'.*.xlf')):
        xlf=E.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
        strings={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
        translated=E.parse(res)
        for data in translated.iter('data'):
            if data.get('name') in strings:data.find('value').text=strings[data.get('name')]
        localized=folder/('Strings.'+culture+'.resx');translated.write(localized,encoding='utf-8',xml_declaration=True)
        E.SubElement(items,'EmbeddedResource',Include=relative(localized),LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
        localizations.append({'assembly':name,'resource':logical,'culture':culture,'strings':{d.get('name'):d.find('value').text or '' for d in translated.iter('data')}})
    contract_folder=folder/'contract';contract_folder.mkdir()
    contract=E.Element('Project',Sdk='Microsoft.NET.Sdk');cp=E.SubElement(contract,'PropertyGroup')
    for k,v in dict(values,TargetFramework='net8.0',Nullable='annotations',ProduceReferenceAssembly='true',AssemblyOriginatorKeyFile='../Library.public.snk').items():
        # Relative library paths in the nested contract have a different base.
        if k in {'CommonPath','CoreLibSharedDir','LibrariesProjectRoot'}:v=v
        E.SubElement(cp,k).text=v
    ci=E.SubElement(contract,'ItemGroup')
    for dep,ver in library['dependencies'].items():E.SubElement(ci,'PackageReference',Include=dep,Version='['+ver+']')
    refs=E.parse(root/name/'ref'/(name+'.csproj')).getroot()
    for group in refs.findall('ItemGroup'):
        for entry in group.findall('Compile'):
            include=entry.get('Include');assert include,name
            if include.startswith('$(CommonPath)'):
                path=root/'Common/src'/include[len('$(CommonPath)'):].replace('\\','/')
            elif include.startswith('$(CoreLibSharedDir)'):
                path=root/'System.Private.CoreLib/src'/include[len('$(CoreLibSharedDir)'):].replace('\\','/')
            else:
                assert '$(' not in include,(name,include)
                path=root/name/'ref'/include.replace('\\','/')
            entry=E.fromstring(E.tostring(entry));entry.set('Include',relative(path,contract_folder))
            if group.get('Condition'):entry.set('Condition','('+group.get('Condition')+') and ('+(entry.get('Condition') or 'true')+')')
            ci.append(entry)
    E.indent(contract);E.ElementTree(contract).write(contract_folder/'Contract.csproj',encoding='utf-8',xml_declaration=True)
    if framework.endswith('-windows'):
        E.SubElement(props,'NuspecFile').text='Package.nuspec'
        E.SubElement(props,'NuspecBasePath').text='$(MSBuildThisFileDirectory)'
        nuspec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
        metadata=E.SubElement(nuspec,'metadata')
        for k,v in {'id':name,'version':version,'authors':'Microsoft','description':upstream.findtext('./PropertyGroup/PackageDescription') or name}.items():E.SubElement(metadata,k).text=v
        E.SubElement(metadata,'license',type='expression').text='MIT'
        E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/runtime',branch='v8.0.31')
        deps=E.SubElement(E.SubElement(metadata,'dependencies'),'group',targetFramework='net8.0')
        for dep,ver in library['dependencies'].items():E.SubElement(deps,'dependency',id=dep,version='['+ver+']')
        files=E.SubElement(nuspec,'files')
        E.SubElement(files,'file',src='bin/Release/'+framework+'/'+name+'.dll',target='runtimes/win/lib/net8.0/')
        E.SubElement(files,'file',src='contract/obj/Release/net8.0/ref/'+name+'.dll',target='ref/net8.0/')
        E.indent(nuspec);E.ElementTree(nuspec).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
    E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)

(output/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
feed=output.parent/'feed'
native=lambda path:subprocess.check_output(['cygpath','-am',str(path)],text=True).strip() if sys.platform.startswith(('cygwin','msys')) else str(path)
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
E.SubElement(feeds,'add',key='private-source-built',value=native(feed))
installed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
E.SubElement(feeds,'add',key='installed-source-built',value=native(installed))
E.indent(config);E.ElementTree(config).write(output/'NuGet.config',encoding='utf-8',xml_declaration=True)
