"""Stage the MEF2 and pipelines prerequisites for Roslyn Workspaces from pinned runtime sources."""
import json
import shutil
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as E

source, output = (Path(x).resolve() for x in sys.argv[1:])
output.mkdir()
inputs = Path(__file__).resolve().parent
libraries = json.loads((inputs/'libraries.json').read_text())
shutil.copyfile(inputs/'README.md',output/'README.md')
removed=[]
for f in source.rglob('*'):
    if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.so','.a','.lib','.winmd','.res'}:
        removed.append(str(f.relative_to(source)));f.unlink()
(output/'removed-binaries.json').write_text(json.dumps(sorted(removed),indent=2)+'\n')
# Normalize source paths before passing them to MSBuild. Its resource task can
# reject an unnormalized path longer than MAX_PATH even when the resolved path
# exists and is shorter. Convert the root only, preserving wildcard characters.
common=Path(os.path.commonpath([source,output]))
source_native=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if sys.platform.startswith(('cygwin','msys')) else str(common)
def source_path(path):
    return source_native+'/'+Path(path).resolve().relative_to(common).as_posix()
root=source/'src/libraries'
localizations=[]

for library in libraries:
    name,version,framework=(library[k] for k in ('id','version','framework'))
    original=root/name/'src'/(name+'.csproj')
    upstream=E.parse(original).getroot()
    servicing=upstream.findtext('./PropertyGroup/ServicingVersion') or '0'
    assert version=='8.0.'+servicing,(name,version,servicing)
    key_props=root/name/'Directory.Build.props'
    key=upstream.findtext('./PropertyGroup/StrongNameKeyId') or (E.parse(key_props).findtext('./PropertyGroup/StrongNameKeyId') if key_props.exists() else None) or 'Open'
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
    project_deps={Path(e.get('Include').replace('\\','/')).stem for e in upstream.iter('ProjectReference')}
    assert project_deps==set(library['dependencies']),(name,project_deps,library['dependencies'])
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
        'PackageReadmeFile':'README.md','RepositoryUrl':'https://github.com/dotnet/runtime','RepositoryType':'git',
        'ImportDirectoryBuildProps':'false','ImportDirectoryBuildTargets':'false',
    }
    for k,v in values.items():E.SubElement(props,k).text=v
    E.SubElement(p,'Import',Project='upstream.proj')
    items=E.SubElement(p,'ItemGroup')
    attribute=E.SubElement(items,'AssemblyAttribute',Include='System.CLSCompliantAttribute')
    E.SubElement(attribute,'_Parameter1').text='true'
    E.SubElement(items,'None',Include=source_path(output/'README.md'),Pack='true',PackagePath='/')
    for dep,ver in library['dependencies'].items():E.SubElement(items,'PackageReference',Include=dep,Version='['+ver+']')
    res=original.parent/'Resources/Strings.resx'
    if res.exists():
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
    E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)

(output/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
feed=output.parent/'feed'
native=lambda path:subprocess.check_output(['cygpath','-am',str(path)],text=True).strip() if sys.platform.startswith(('cygwin','msys')) else str(path)
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
E.SubElement(feeds,'add',key='private-source-built',value=native(feed))
installed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
E.SubElement(feeds,'add',key='installed-source-built',value=native(installed))
E.indent(config);E.ElementTree(config).write(output/'NuGet.config',encoding='utf-8',xml_declaration=True)
