"""Preserve complete original ClientModel project and C# for the source.NET8 graph."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
name='System.ClientModel';folder=source/'sdk/core/System.ClientModel/src';rel=lambda p:os.path.relpath(p,out).replace('\\','/')
inputs=json.loads((here/'source-inputs.json').read_text());meta=json.loads((here/'published-metadata.json').read_text())[0]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,digest in inputs['original_project_tree_sha256'].items():assert sha(source/relative)==digest,relative
key=source/'eng/AzureSDKClient.snk';blob=key.read_bytes()
if blob[0]==7:
    assert blob[8:12]==b'RSA2';bits=struct.unpack_from('<I',blob,12)[0]
    public_blob=bytes([6])+blob[1:8]+b'RSA1'+blob[12:20+bits//8]
    public=struct.pack('<III',0x2400,0x8004,len(public_blob))+public_blob
else:public=blob
assert public.hex()==meta['public_key']
original=folder/(name+'.csproj');tree=E.parse(original);tree.getroot().attrib.pop('Sdk')
for item in tree.iter('PackageReference'):
    assert item.get('Include') in ['System.Memory.Data','System.Text.Json']
    item.set('Version','[1.0.2]' if item.get('Include')=='System.Memory.Data' else '[8.0.5]')
E.indent(tree);tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',TargetFramework='net8.0').items():E.SubElement(props,k).text=v
E.SubElement(p,'Import',Project='upstream.proj');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,RootNamespace=name,Version='1.0.0',
 AssemblyVersion=meta['version'],FileVersion=meta['attributes']['AssemblyFileVersionAttribute'],
 InformationalVersion=meta['attributes']['AssemblyInformationalVersionAttribute'],IncludeSourceRevisionInInformationalVersion='false',
 SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=rel(key),EnableNETAnalyzers='false',NuGetAudit='false',
 GenerateDocumentationFile='true',GeneratePackageOnBuild='false',NoWarn='$(NoWarn);CS1591',LangVersion='12.0').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup');files=sorted(folder.rglob('*.cs'));assert len(files)==11
for path in files:E.SubElement(items,'Compile',Include=rel(path))
capture=E.SubElement(p,'Target',Name='CaptureOriginalCompilerInputs',BeforeTargets='CoreCompile')
for kind,filename in [('Compile','compiler-inputs.txt'),('ReferencePath','reference-inputs.txt')]:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+filename,Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.indent(p);E.ElementTree(p).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip() if __import__('shutil').which('cygpath') else '/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
metadata=['Directory.Build.props','Directory.Build.targets','eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','sdk/core/System.ClientModel/Directory.Build.props','sdk/core/System.ClientModel/src/System.ClientModel.csproj']
r=dict(source_commit=inputs['source_repository']['commit'],source_archive_sha256=inputs['source_archive_sha256'],
 original_project_tree=inputs['original_project_tree_sha256'],original_cs={path.relative_to(source).as_posix():sha(path) for path in files},
 original_project_metadata={path:sha(source/path) for path in metadata},signing_key_sha256=sha(key),production_cs_changes=[],
 prepared_project_metadata={path:sha(out/path) for path in ['Library.csproj','upstream.proj']},
 source_dependencies={'System.Memory.Data':'1.0.2','System.Text.Json':'8.0.5'},status='source-preparation-complete-build-runtime-and-packaging-unverified')
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS complete original ClientModel project/tree,11 unchanged C# inputs and original Azure client public-key identity')
