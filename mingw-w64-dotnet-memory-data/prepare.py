"""Preserve complete original BinaryData sources/imported project for source.NET8."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
name='System.Memory.Data';folder=source/'sdk/core/System.Memory.Data/src';rel=lambda p:os.path.relpath(p,out).replace('\\','/')
proof=json.loads((here/'git-tree-provenance.json').read_text());gold=json.loads((here/'published-identity.json').read_text())
for item in proof['files']:
    data=(source/item['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==item['sha256']
    assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['git_blob']
key=folder/'Open.snk';blob=key.read_bytes()
# Azure's original Open.snk contains the openly published Open signing pair,
# whereas PE metadata stores its strong-name public blob. Compare that blob.
assert blob[0]==7 and blob[8:12]==b'RSA2'
bits=struct.unpack_from('<I',blob,12)[0]
public_blob=bytes([6])+blob[1:8]+b'RSA1'+blob[12:20+bits//8]
public=struct.pack('<III',0x2400,0x8004,len(public_blob))+public_blob
assert public.hex()==gold['public_key']
tree=E.parse(folder/(name+'.csproj'));tree.getroot().attrib.pop('Sdk')
for group in tree.getroot():
    for item in list(group):
        if item.tag=='PackageReference':
            if item.get('Include')=='System.Text.Encodings.Web':group.remove(item)
            else:
                assert item.get('Include')=='System.Text.Json';item.set('Version','[8.0.5]')
E.indent(tree);tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for prop,value in dict(ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',TargetFramework='net8.0').items():E.SubElement(props,prop).text=value
E.SubElement(project,'Import',Project='upstream.proj');props=E.SubElement(project,'PropertyGroup')
for prop,value in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,RootNamespace='System',Version='1.0.2',
    AssemblyVersion=gold['version'],FileVersion=gold['attributes']['AssemblyFileVersionAttribute'],
    InformationalVersion=gold['attributes']['AssemblyInformationalVersionAttribute'],IncludeSourceRevisionInInformationalVersion='false',
    SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=rel(key),EnableNETAnalyzers='false',NuGetAudit='false',
    GenerateDocumentationFile='true',NoWarn='CS1591',GeneratePackageOnBuild='false').items():E.SubElement(props,prop).text=value
items=E.SubElement(project,'ItemGroup')
files=sorted(folder.glob('*.cs'));assert len(files)==2
for path in files:E.SubElement(items,'Compile',Include=rel(path))
capture=E.SubElement(project,'Target',Name='CaptureOriginalCompilerInputs',BeforeTargets='CoreCompile')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)compiler-inputs.txt',Lines="@(Compile->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)reference-inputs.txt',Lines="@(ReferencePath->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.indent(project);E.ElementTree(project).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip() if shutil.which('cygpath') else '/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
metadata=['Directory.Build.props','Directory.Build.targets','eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','sdk/core/System.Memory.Data/Directory.Build.props','sdk/core/System.Memory.Data/src/System.Memory.Data.csproj']
assert all((source/p).is_file() for p in metadata)
(out/'source-inventory.json').write_text(json.dumps(dict(source_commit=proof['commit'],
 source_archive_sha256='a6cb4b058f24a49b8c62594723d171f8b782026fce5d7d0274c0282472189317',git_tree_files=proof['files'],
 original_cs={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
 original_project_metadata={p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in metadata},
 prepared_project_metadata={p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in ['Library.csproj','upstream.proj']},
 production_cs_changes=[],framework_provided=['System.Text.Encodings.Web'],source_dependencies={'System.Text.Json':'8.0.5'}),indent=2)+'\n')
print('PASS complete original BinaryData src tree Git blob/SHA256 hashes and both unchanged source files')
