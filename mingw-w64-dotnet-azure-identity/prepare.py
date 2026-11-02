"""Retain the complete original Azure.Identity project and its explicit shared inputs."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
name='Azure.Identity';folder=source/'sdk/identity/Azure.Identity/src';rel=lambda p:os.path.relpath(p,out).replace('\\','/')
inputs=json.loads((here/'source-inputs.json').read_text());meta=json.loads((here/'published-metadata.json').read_text())[0]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for mapping in ['original_project_tree_sha256','original_explicit_shared_sha256']:
    for path,digest in inputs[mapping].items():assert sha(source/path)==digest,path
key=source/'eng/AzureSDKClient.snk';blob=key.read_bytes();assert blob[0]==7 and blob[8:12]==b'RSA2'
bits=struct.unpack_from('<I',blob,12)[0];public_blob=bytes([6])+blob[1:8]+b'RSA1'+blob[12:20+bits//8]
public=struct.pack('<III',0x2400,0x8004,len(public_blob))+public_blob;assert public.hex()==meta['public_key']
original=folder/(name+'.csproj');tree=E.parse(original);tree.getroot().attrib.pop('Sdk')
files=set(folder.rglob('*.cs'));shared=[]
dependencies={'Azure.Core':'1.38.0','System.Text.Json':'8.0.5','Microsoft.Identity.Client':'4.61.3','Microsoft.Identity.Client.Extensions.Msal':'4.61.3','System.Security.Cryptography.ProtectedData':'8.0.0'}
framework={'System.Memory','System.Threading.Tasks.Extensions'}
for group in tree.getroot().findall('ItemGroup'):
    for item in list(group):
        if item.tag=='Compile':
            value=item.get('Include');assert value.startswith('$(AzureCoreSharedSources)')
            path=source/'sdk/core/Azure.Core/src/Shared'/value[len('$(AzureCoreSharedSources)'):]
            assert path.relative_to(source).as_posix() in inputs['original_explicit_shared_sha256']
            files.add(path);shared.append(path.relative_to(source).as_posix());group.remove(item)
        elif item.tag=='PackageReference':
            dependency=item.get('Include')
            if dependency in dependencies:item.set('Version','['+dependencies[dependency]+']')
            else:assert dependency in framework;group.remove(item)
assert len(shared)==15
E.indent(tree);tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',TargetFramework='net8.0').items():E.SubElement(props,k).text=v
E.SubElement(p,'Import',Project='upstream.proj');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',TargetFrameworks='',AssemblyName=name,RootNamespace=name,Version='1.11.4',
 AssemblyVersion=meta['version'],FileVersion=meta['attributes']['AssemblyFileVersionAttribute'],
 InformationalVersion=meta['attributes']['AssemblyInformationalVersionAttribute'],IncludeSourceRevisionInInformationalVersion='false',
 SignAssembly='true',PublicSign='false',AssemblyOriginatorKeyFile=rel(key),EnableNETAnalyzers='false',NuGetAudit='false',
 GenerateDocumentationFile='true',GeneratePackageOnBuild='false',LangVersion='12.0').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
changed='sdk/identity/Azure.Identity/src/Credentials/AuthorizationCodeCredential.cs'
overlay=out/'overlays/AuthorizationCodeCredential.cs';overlay.parent.mkdir()
data=(source/changed).read_bytes();old=b'            AccessToken token;';new=b'            AccessToken token = default;'
assert data.count(old)==1;overlay.write_bytes(data.replace(old,new))
for path in sorted(files):E.SubElement(items,'Compile',Include=rel(overlay if path==source/changed else path))
capture=E.SubElement(p,'Target',Name='CaptureOriginalCompilerInputs',BeforeTargets='CoreCompile')
for kind,filename in [('Compile','compiler-inputs.txt'),('ReferencePath','reference-inputs.txt')]:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+filename,Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.indent(p);E.ElementTree(p).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip() if __import__('shutil').which('cygpath') else '/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
metadata=['Directory.Build.props','Directory.Build.targets','eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','sdk/identity/Azure.Identity/Directory.Build.props','sdk/identity/Azure.Identity/src/Azure.Identity.csproj']
r=dict(source_commit=inputs['source_repository']['commit'],source_archive_sha256=inputs['source_archive_sha256'],
 original_project_tree=inputs['original_project_tree_sha256'],original_cs={path.relative_to(source).as_posix():sha(path) for path in sorted(files)},
 original_project_metadata={path:sha(source/path) for path in metadata},original_selected_shared=shared,original_explicit_shared=inputs['original_explicit_shared_sha256'],
 signing_key_sha256=sha(key),production_cs_changes=[dict(path=changed,overlay='overlays/AuthorizationCodeCredential.cs',original_sha256=sha(source/changed),prepared_sha256=sha(overlay),reason='Initialize the AccessToken local passed to a helper that overwrites its token parameter before reading; required for NET8 definite assignment')],prepared_project_metadata={path:sha(out/path) for path in ['Library.csproj','upstream.proj']},
 source_dependencies=dependencies,framework_provided=sorted(framework))
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS complete original Azure.Identity project and '+str(len(files))+' C# inputs:131 unchanged, one explicit default-initializer port; all15 original shared files retained')
