"""Build original Utilities16 NS2 with the original exact dependency versions."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=(Path(x).resolve() for x in sys.argv[1:3]);assert not sys.argv[3:] or len(sys.argv)==5 and sys.argv[3]=='--feed';assert not out.exists();out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='04907cbf4ade0101998006e955d7c5ca567e19342340ee71fcd36612158c6726'
commit='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0';source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==commit
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2]
        if not (name.startswith(('src/Utilities/','src/Shared/')) or name in {'src/Directory.BeforeCommon.targets','src/Directory.Build.props','Directory.Build.props','eng/Packages.props','src/MSFT.snk','LICENSE','THIRDPARTYNOTICES.txt'}):continue
        data=t.extractfile(m).read()
        if name.lower().endswith(('.dll','.exe','.pdb','.nupkg')) or data[:2]==b'MZ':continue
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
original=source/'src/Utilities/Microsoft.Build.Utilities.csproj';upstream=E.parse(original).getroot();upstream.attrib.pop('Sdk')
versions={'System.Collections.Immutable':'1.5.0','System.Text.Encoding.CodePages':'4.0.1','Microsoft.Win32.Registry':'4.3.0','Microsoft.Build.Framework':'16.0.461'}
for item in upstream.iter():
    if item.tag=='Import':item.set('Project',native((original.parent/item.get('Project').replace('\\','/')).resolve()))
    if item.tag=='ProjectReference':
        assert item.get('Include')=='..\\Framework\\Microsoft.Build.Framework.csproj';item.tag='PackageReference';item.set('Include','Microsoft.Build.Framework');item.set('Version','[16.0.461]')
    elif item.tag=='PackageReference' and item.get('Include') in versions:item.set('Version','['+versions[item.get('Include')]+']')
    if item.tag in {'Compile','EmbeddedResource','None'}:
        for attr in ['Include','Remove','Update']:
            if item.get(attr):item.set(attr,native(original.parent)+'/'+item.get(attr).replace('\\','/'))
E.indent(upstream);E.ElementTree(upstream).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
values=dict(TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',TargetFrameworkVersion='v2.0',LibraryTargetFrameworks='netstandard2.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName='Microsoft.Build.Utilities.Core',RootNamespace='Microsoft.Build.Utilities',Configuration='Release',OsEnvironment='windows',DisableNerdbankVersioning='true',GenerateAssemblyInfo='false',GenerateDocumentationFile='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(source/'src/MSFT.snk'),TreatWarningsAsErrors='true',NuGetAudit='false',LangVersion='7.3',UseSharedCompilation='false',EnableNETAnalyzers='false',PackageId='Microsoft.Build.Utilities.Core',Version='16.0.461',PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/microsoft/msbuild',RepositoryCommit=commit)
values.update(AppendTargetFrameworkToOutputPath='false',OutputPath='bin/Release/',IntermediateOutputPath='obj/Release/')
warnings=[]
for file in [source/'Directory.Build.props',source/'src/Directory.Build.props']:
    for item in E.parse(file).iter():
        if item.tag.rsplit('}',1)[-1]=='NoWarn':warnings.append(item.text.replace('$(NoWarn)','').strip(';'))
values['NoWarn']=';'.join(warnings)
for k,v in values.items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
for p in sorted(original.parent.rglob('*.cs')):E.SubElement(items,'Compile',Include=native(p))
for p in sorted(original.parent.rglob('*.resx')):E.SubElement(items,'EmbeddedResource',Include=native(p))
E.SubElement(tree,'Import',Project='upstream.proj');E.SubElement(tree,'Import',Project=native(source/'src/Directory.BeforeCommon.targets'))
extra=E.SubElement(tree,'ItemGroup');E.SubElement(extra,'Compile',Include='BootstrapVersion.cs')
(out/'BootstrapVersion.cs').write_text('[assembly:System.Reflection.AssemblyVersion("15.1.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("16.0.461.62831")]\n[assembly:System.Reflection.AssemblyInformationalVersion("16.0.461+g6ff56ef63c")]\n[assembly:System.Reflection.AssemblyConfiguration("Release")]\n')
for license in ['LICENSE','THIRDPARTYNOTICES.txt']:E.SubElement(extra,'None',Include=native(source/license),Pack='true',PackagePath='/')
capture=E.SubElement(tree,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
E.indent(tree);E.ElementTree(tree).write(out/'Utilities.csproj',encoding='utf-8',xml_declaration=True)
if len(sys.argv)==5:
    config='<configuration><packageSources><clear/><add key="candidate" value="'+native(Path(sys.argv[4]))+'"/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources><packageSourceMapping><packageSource key="candidate"><package pattern="Microsoft.Win32.Registry"/><package pattern="System.Text.Encoding.CodePages"/></packageSource><packageSource key="source"><package pattern="*"/></packageSource></packageSourceMapping></configuration>\n'
else:config='<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n'
(out/'NuGet.config').write_text(config)
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_file_sha256=hashes,production_CSharp_changes=0,original_frameworks=['net472','netstandard2.0'],compiled_framework='netstandard2.0',exact_original_dependency_versions=versions,NET472_profile_built=False,original_Nerdbank_toolchain_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original Utilities16 NS2 source/project imports and exact dependencies prepared')
