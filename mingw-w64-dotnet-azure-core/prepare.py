"""Replay the complete original Azure.Core project selection for source.NET8."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
name='Azure.Core';folder=source/'sdk/core/Azure.Core/src';rel=lambda p:os.path.relpath(p,out).replace('\\','/')
inputs=json.loads((here/'source-inputs.json').read_text());meta=json.loads((here/'published-metadata.json').read_text())[0]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,digest in inputs['original_project_tree_sha256'].items():assert sha(source/path)==digest,path
key=source/'eng/AzureSDKClient.snk';blob=key.read_bytes()
assert blob[0]==7 and blob[8:12]==b'RSA2'
bits=struct.unpack_from('<I',blob,12)[0];public_blob=bytes([6])+blob[1:8]+b'RSA1'+blob[12:20+bits//8]
public=struct.pack('<III',0x2400,0x8004,len(public_blob))+public_blob
assert public.hex()==meta['public_key']
original=folder/(name+'.csproj');tree=E.parse(original);tree.getroot().attrib.pop('Sdk')
# The original SDK includes all *.cs, then removes Shared/**/*.cs and restores
# its explicit shared-file list. Replay that exact selection before importing.
files={p for p in folder.rglob('*.cs') if p.relative_to(folder).parts[0]!='Shared'}
selected=[];removed=[]
for group in tree.getroot().findall('ItemGroup'):
    for item in list(group):
        if item.tag!='Compile':continue
        assert not item.get('Condition') and not group.get('Condition')
        if item.get('Remove'):
            assert item.get('Remove')=='Shared\\**\\*.cs';removed.append(item.get('Remove'))
        else:
            path=item.get('Include').replace('\\','/');assert path.startswith('Shared/') and (folder/path).is_file()
            selected.append(path);files.add(folder/path)
        group.remove(item)
assert removed==['Shared\\**\\*.cs'] and len(selected)==len(set(selected))==32
dependencies={'System.ClientModel':'1.0.0','System.Memory.Data':'1.0.2','System.Text.Json':'8.0.5'}
framework={'Microsoft.Bcl.AsyncInterfaces','System.Numerics.Vectors','System.Diagnostics.DiagnosticSource','System.Threading.Tasks.Extensions','System.Text.Encodings.Web'}
for group in tree.getroot().findall('ItemGroup'):
    for item in list(group):
        if item.tag!='PackageReference':continue
        dependency=item.get('Include')
        if dependency in dependencies:item.set('Version','['+dependencies[dependency]+']')
        elif dependency in framework or (group.get('Condition') and "'net461'" in group.get('Condition')):group.remove(item)
        else:raise AssertionError(dependency)
E.indent(tree);tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',TargetFramework='net8.0').items():E.SubElement(props,k).text=v
E.SubElement(p,'Import',Project='upstream.proj');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,RootNamespace=name,Version='1.38.0',
 AssemblyVersion=meta['version'],FileVersion=meta['attributes']['AssemblyFileVersionAttribute'],
 InformationalVersion=meta['attributes']['AssemblyInformationalVersionAttribute'],IncludeSourceRevisionInInformationalVersion='false',
 SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=rel(key),EnableNETAnalyzers='false',NuGetAudit='false',
 GenerateDocumentationFile='true',GeneratePackageOnBuild='false',LangVersion='12.0',EmitCompilerGeneratedFiles='true').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
for path in sorted(files):E.SubElement(items,'Compile',Include=rel(path))
capture=E.SubElement(p,'Target',Name='CaptureOriginalCompilerInputs',BeforeTargets='CoreCompile')
for kind,filename in [('Compile','compiler-inputs.txt'),('ReferencePath','reference-inputs.txt'),('Analyzer','analyzer-inputs.txt')]:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+filename,Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.indent(p);E.ElementTree(p).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip() if __import__('shutil').which('cygpath') else '/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
metadata=['Directory.Build.props','Directory.Build.targets','eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','sdk/core/Azure.Core/Directory.Build.props','sdk/core/Azure.Core/src/Azure.Core.csproj']
r=dict(source_commit=inputs['source_repository']['commit'],source_archive_sha256=inputs['source_archive_sha256'],
 original_project_tree=inputs['original_project_tree_sha256'],original_cs={path.relative_to(source).as_posix():sha(path) for path in sorted(files)},
 original_project_metadata={path:sha(source/path) for path in metadata},signing_key_sha256=sha(key),production_cs_changes=[],
 prepared_project_metadata={path:sha(out/path) for path in ['Library.csproj','upstream.proj']},original_selected_shared=selected,
 framework_provided=sorted(framework),source_dependencies=dependencies)
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS complete original Azure.Core project/tree and '+str(len(files))+' unchanged C# selected by original Shared rules')
