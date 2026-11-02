"""Original Framework16 NS2 port with proven unused package-reference pruning."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='04907cbf4ade0101998006e955d7c5ca567e19342340ee71fcd36612158c6726'
source=out/'source';source.mkdir();originals={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0'
    wanted={'src/Shared/Constants.cs','src/Shared/BinaryWriterExtensions.cs','src/Directory.BeforeCommon.targets','src/Directory.Build.props','src/MSFT.snk','Directory.Build.props','eng/Packages.props','LICENSE','THIRDPARTYNOTICES.txt'}
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2]
        if name not in wanted and not name.startswith('src/Framework/'):continue
        data=t.extractfile(m).read()
        assert not name.lower().endswith(('.dll','.exe','.pdb','.nupkg')) and data[:2]!=b'MZ',name
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        originals[name]=hashlib.sha256(data).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
original=source/'src/Framework/Microsoft.Build.Framework.csproj'
upstream=E.parse(original).getroot();upstream.attrib.pop('Sdk')
for item in upstream.iter():
    if item.tag not in {'Compile','EmbeddedResource','None'}:continue
    for attr in ['Include','Remove','Update']:
        value=item.get(attr)
        if value:item.set(attr,native(original.parent)+'/'+value.replace('\\','/'))
E.indent(upstream);E.ElementTree(upstream).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
key=(source/'src/MSFT.snk').read_bytes();assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
values=dict(TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',TargetFrameworkVersion='v2.0',LibraryTargetFrameworks='netstandard2.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName='Microsoft.Build.Framework',RootNamespace='Microsoft.Build.Framework',Configuration='Release',OsEnvironment='windows',DisableNerdbankVersioning='true',GenerateAssemblyInfo='false',AppendTargetFrameworkToOutputPath='false',OutputPath='bin/Release/',IntermediateOutputPath='obj/Release/',GenerateDocumentationFile='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(source/'src/MSFT.snk'),TreatWarningsAsErrors='true',NuGetAudit='false',LangVersion='7.3',UseSharedCompilation='false',EnableNETAnalyzers='false',IsPackable='true',PackageId='Microsoft.Build.Framework',Version='16.0.461',PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/microsoft/msbuild',RepositoryCommit='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0')
no_warn=[]
for p in [source/'Directory.Build.props',source/'src/Directory.Build.props']:
    for item in E.parse(p).iter():
        if item.tag.rsplit('}',1)[-1]=='NoWarn':no_warn.append(item.text.replace('$(NoWarn)','').strip(';'))
values['NoWarn']=';'.join(no_warn)
for name,value in values.items():E.SubElement(pg,name).text=value
items=E.SubElement(tree,'ItemGroup')
for path in sorted(original.parent.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(path))
for path in sorted(original.parent.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(path))
E.SubElement(tree,'Import',Project='upstream.proj')
E.SubElement(tree,'Import',Project=native(source/'src/Directory.BeforeCommon.targets'))
# Capture the original declarations before pruning only this preliminary build.
declarations={e.get('Include') for e in upstream.iter('PackageReference')}
assert declarations=={'System.Runtime.Serialization.Primitives','System.Threading.Thread'}
remove=E.SubElement(tree,'ItemGroup')
E.SubElement(remove,'PackageReference',Remove=';'.join(sorted(declarations)))
assembly_info=out/'BootstrapVersion.cs';assembly_info.write_text('[assembly:System.Reflection.AssemblyVersion("15.1.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("16.0.461.62831")]\n[assembly:System.Reflection.AssemblyInformationalVersion("16.0.461+g6ff56ef63c")]\n[assembly:System.Reflection.AssemblyConfiguration("Release")]\n')
E.SubElement(remove,'Compile',Include='BootstrapVersion.cs')
for license in ['LICENSE','THIRDPARTYNOTICES.txt']:
    assert (source/license).exists()
    E.SubElement(remove,'None',Include=native(source/license),Pack='true',PackagePath='/')
capture=E.SubElement(tree,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:
    E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(Nullable)|$(TreatWarningsAsErrors)',Overwrite='true')
E.indent(tree);E.ElementTree(tree).write(out/'Framework.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0',source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_file_sha256=originals,original_project='src/Framework/Microsoft.Build.Framework.csproj',original_frameworks=['net472','netstandard2.0'],compiled_framework='netstandard2.0',production_source_changes=0,pruned_unused_NS2_package_references={'System.Runtime.Serialization.Primitives':'4.1.1','System.Threading.Thread':'4.0.0'},dependency_pruning_requires_original_API_and_assembly_reference_equality=True,original_release_file_version='16.0.461.62831',original_release_informational_version='16.0.461+g6ff56ef63c',original_Nerdbank_toolchain_replayed=False,NET472_profile_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original Framework16 inputs and feature-policy import; unused NS2 package pruning requires exact ABI/runtime-reference verification')
