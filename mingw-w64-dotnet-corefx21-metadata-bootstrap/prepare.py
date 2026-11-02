"""Prepare the exact CoreFX 2.1 Immutable/Metadata netstandard2.0 sources."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='a886ecc798d92fa1183eb127f95ceb47270be7a53fcae51e7f391523c261e586'
commit='30ab651fcb4354552bd4891619a0bdd81e0ebdbf'
names={'System.Collections.Immutable':'1.5.0','System.Reflection.Metadata':'1.6.0'}
source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==commit
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2]
        if not (name in {'LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','dir.props','dir.targets','src/dir.props','src/dir.targets'} or name.startswith('src/Common/src/') or any(name.startswith(('src/'+n+'/src/','src/'+n+'/ref/')) for n in names)):continue
        if name.lower().endswith(('.dll','.exe','.pdb','.nupkg')):continue
        data=t.extractfile(m).read();assert data[:2]!=b'MZ',name
        dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
key=Path(__file__).parent/'inputs/Microsoft.snk'
assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
baseline=json.loads((Path(__file__).parent/'inputs/published-ns2-metadata.json').read_text())
records={}
for name,version in names.items():
    folder=out/name;folder.mkdir();original=source/'src'/name/'src'/(name+'.csproj')
    upstream=E.parse(original).getroot()
    # Preserve original conditions and compile selections, adapting the legacy
    # build-host imports and framework reference resolution to source SDK 8.
    for e in upstream.iter():e.tag=e.tag.rsplit('}',1)[-1]
    for child in list(upstream):
        if child.tag=='Import':upstream.remove(child)
    for group in upstream.findall('ItemGroup'):
        for item in list(group):
            if item.tag in {'Reference','ProjectReference'}:group.remove(item)
            else:
                for attr in ['Include','Remove','Update']:
                    if item.get(attr):
                        value=item.get(attr).replace('\\','/')
                        item.set(attr,value if value.startswith('$(CommonPath)') else native(original.parent)+'/'+value)
    E.indent(upstream);E.ElementTree(upstream).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    values=dict(TargetFramework='netstandard2.0',TargetGroup='netstandard',ConfigurationGroup='Release',Platform='AnyCPU',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName=name,RootNamespace=name,CommonPath=native(source/'src/Common/src'),GenerateAssemblyInfo='false',GenerateTargetFrameworkAttribute='false',GenerateDocumentationFile='true',TreatWarningsAsErrors='true',WarningLevel='4',LangVersion='7.3',Nullable='disable',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(key),NuGetAudit='false',UseSharedCompilation='false',EnableNETAnalyzers='false',PackageId=name,Version=version,IsPackable='true',PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/corefx',RepositoryCommit=commit)
    for k,v in values.items():E.SubElement(pg,k).text=v
    E.SubElement(tree,'Import',Project='upstream.proj')
    items=E.SubElement(tree,'ItemGroup')
    if name=='System.Reflection.Metadata':E.SubElement(items,'PackageReference',Include='System.Collections.Immutable',Version='[1.5.0]')
    E.SubElement(items,'Compile',Include=native(source/'src/Common/src/System/SR.cs'))
    E.SubElement(items,'Compile',Include='SR.Generated.cs');E.SubElement(items,'Compile',Include='BootstrapVersion.cs')
    resource=original.parent/'Resources/Strings.resx'
    logical='FxResources.'+name+'.SR'
    E.SubElement(items,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
    code=['namespace FxResources.'+name+' {internal static class SR {}}','namespace System {internal partial class SR {private static System.Type ResourceType => typeof('+logical+');']
    resource_values={}
    for entry in E.parse(resource).findall('data'):
        ident=entry.get('name');assert ident.isidentifier();resource_values[ident]=entry.findtext('value')
        code.append('internal static string @'+ident+' => GetResourceString("'+ident+'", null);')
    code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
    identity=baseline[name+'.dll']['identity'];assembly_version=identity.split('Version=')[1].split(',')[0]
    attrs={a['type']:a['arguments'] for a in baseline[name+'.dll']['attributes']}
    info=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(assembly_version)+')]','[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(attrs['System.Reflection.AssemblyFileVersionAttribute'][0])+')]','[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps('Source-built CoreFX '+commit+'; source SDK8/csc4.4 bootstrap')+')]','[assembly:System.CLSCompliant('+('false' if name=='System.Reflection.Metadata' else 'true')+')]']
    (folder/'BootstrapVersion.cs').write_text('\n'.join(info)+'\n')
    for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:E.SubElement(items,'None',Include=native(source/lic),Pack='true',PackagePath='/')
    capture=E.SubElement(tree,'Target',Name='CaptureSourceInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(TargetGroup)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
    E.indent(tree);E.ElementTree(tree).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
    records[name]=dict(version=version,assembly_version=assembly_version,resources=resource_values,original_project=str(original.relative_to(source)))
(out/'feed').mkdir()
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="candidate" value="'+native(out/'feed')+'"/><add key="installed" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_file_sha256=hashes,libraries=records,production_CSharp_changes=0,compiled_profile='netstandard2.0',other_original_profiles_built=False,original_buildtools_host_replayed=False),indent=2)+'\n')
print('PASS prepared original CoreFX Immutable1.5/Metadata1.6 NS2 inputs')
