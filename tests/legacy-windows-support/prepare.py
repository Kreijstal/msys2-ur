"""Prepare original Windows Registry/CodePages NS1.3 source builds."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

registry,codepages,out=(Path(x).resolve() for x in sys.argv[1:4]);assert not out.exists();out.mkdir()
assert not sys.argv[4:] or len(sys.argv)==6 and sys.argv[4]=='--references'
here=Path(__file__).parent;baseline=json.loads((here/'inputs/published-runtime-metadata.json').read_text())
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
specs=[('Microsoft.Win32.Registry','4.3.0',registry,'4d1af962ca0fede10beb01d197367c2f90e92c97','1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'),('System.Text.Encoding.CodePages','4.0.1',codepages,'9688ddbb62c04189cac4c4a06e31e93377dccd41','986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601')]
key=here/'inputs/Microsoft.snk';assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
records={};refs=Path(sys.argv[5]).resolve() if len(sys.argv)==6 else Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/ref');assert len(list(refs.glob('*.dll')))==16
if len(sys.argv)==4:subprocess.run(['pacman','-T','mingw-w64-clang-x86_64-dotnet-legacy-ns13-contracts-bootstrap>=20261031-3'],check=True)
for name,version,archive,commit,digest in specs:
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
    folder=out/name;folder.mkdir();source=folder/'source';source.mkdir();hashes={}
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment']==commit
        for m in t:
            if not m.isfile():continue
            rel=m.name.partition('/')[2]
            if not (rel.startswith(('src/'+name+'/src/','src/'+name+'/ref/','src/Common/src/')) or rel in {'dir.props','dir.targets','LICENSE','THIRD-PARTY-NOTICES'}):continue
            data=t.extractfile(m).read();assert data[:2]!=b'MZ' and not rel.endswith(('.dll','.exe','.pdb','.nupkg')),rel
            p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[rel]=hashlib.sha256(data).hexdigest()
    original=source/'src'/name/'src'/(name+'.csproj');upstream=E.parse(original).getroot()
    for item in upstream.iter():item.tag=item.tag.rsplit('}',1)[-1]
    for item in list(upstream):
        if item.tag=='Import':upstream.remove(item)
    for item in upstream.iter():
        if item.tag not in {'Compile','EmbeddedResource','None'}:continue
        for attr in ['Include','Remove','Update']:
            if item.get(attr):
                value=item.get(attr).replace('\\','/');item.set(attr,value if value.startswith('$(CommonPath)') else native(original.parent)+'/'+value)
    E.indent(upstream);E.ElementTree(upstream).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    values=dict(TargetFramework='netstandard1.3',DisableImplicitFrameworkReferences='true',NoStdLib='true',AddAdditionalExplicitAssemblyReferences='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName=name,RootNamespace=name,CommonPath=native(source/'src/Common/src'),Configuration='Release',ConfigurationGroup='Release',OSGroup='Windows_NT',TargetsWindows='true',TargetsUnix='false',TargetGroup='',GenerateAssemblyInfo='false',GenerateTargetFrameworkAttribute='false',TreatWarningsAsErrors='true',LangVersion='6',Nullable='disable',EnableNETAnalyzers='false',CheckEolTargetFramework='false',NuGetAudit='false',UseSharedCompilation='false',AllowUnsafeBlocks='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(key),IsPackable='false')
    for k,v in values.items():E.SubElement(pg,k).text=v
    E.SubElement(tree,'Import',Project='upstream.proj')
    items=E.SubElement(tree,'ItemGroup')
    for ref in sorted(refs.glob('*.dll')):
        node=E.SubElement(items,'Reference',Include=ref.stem);E.SubElement(node,'HintPath').text=native(ref);E.SubElement(node,'Private').text='false'
    E.SubElement(items,'Compile',Include=native(source/'src/Common/src/System/SR.cs'))
    for generated in ['SR.Generated.cs','BootstrapVersion.cs']:E.SubElement(items,'Compile',Include=generated)
    resource=original.parent/'Resources/Strings.resx';logical='FxResources.'+name+'.SR'
    E.SubElement(items,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
    code=['namespace FxResources.'+name+' {internal static class SR {}}','namespace System {internal partial class SR {private static System.Type ResourceType { get { return typeof('+logical+'); } }']
    strings={}
    for entry in E.parse(resource).findall('data'):
        ident=entry.get('name');assert ident.isidentifier();strings[ident]=entry.findtext('value')
        code.append('internal static string @'+ident+' { get { return GetResourceString("'+ident+'", null); } }')
    code.append('}}');(folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
    meta=baseline[name+'.dll'];av=meta['identity'].split('Version=')[1].split(',')[0];attrs={x['type']:x['arguments'] for x in meta['attributes']}
    (folder/'BootstrapVersion.cs').write_text('[assembly:System.Reflection.AssemblyVersion('+json.dumps(av)+')]\n[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(attrs['System.Reflection.AssemblyFileVersionAttribute'][0])+')]\n[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps('Source-built CoreFX '+commit+'; original Windows NS1.3; source SDK8/Csc4.4 bootstrap')+')]\n[assembly:System.CLSCompliant(true)]\n')
    capture=E.SubElement(tree,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
    for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(TargetGroup)|$(TargetsWindows)|$(TargetsUnix)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
    E.indent(tree);E.ElementTree(tree).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
    records[name]=dict(version=version,source_commit=commit,source_archive_sha256=digest,original_file_sha256=hashes,original_project=str(original.relative_to(source)),resources=strings,assembly_version=av,production_CSharp_changes=0,original_target_framework='netstandard1.3',original_legacy_buildtools_host_replayed=False)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
(out/'source-inputs.json').write_text(json.dumps(dict(libraries=records,source_legacy_reference_pack=str(refs),full_dependency_goal_complete=False),indent=2)+'\n');print('PASS prepared original Registry4.3/CodePages4.0.1 Windows NS1.3 inputs')
