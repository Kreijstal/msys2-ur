"""Build original Tasks16 NS2 with the original exact dependency versions."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,arcade,out=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='04907cbf4ade0101998006e955d7c5ca567e19342340ee71fcd36612158c6726'
commit='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0';source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==commit
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2]
        if not (name.startswith(('src/Tasks/','src/Shared/')) or name in {'src/Directory.BeforeCommon.targets','src/Directory.Build.props','Directory.Build.props','eng/Packages.props','eng/Version.Details.xml','global.json','src/MSFT.snk','LICENSE','THIRDPARTYNOTICES.txt'}):continue
        data=t.extractfile(m).read()
        if name.lower().endswith(('.dll','.exe','.pdb','.nupkg')) or data[:2]==b'MZ':continue
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
assert hashlib.sha256(arcade.read_bytes()).hexdigest()=='5e731e4cd049e2c71bb376a69e2535c4bb3983fea5870911336db5d564c37180'
arcade_commit='26e4b7ad355f3c08eea8296d1733ada986d6edf3'
policy_path='src/Microsoft.DotNet.Arcade.Sdk/tools/ProjectDefaults.props'
with tarfile.open(arcade) as t:
    assert t.pax_headers['comment']==arcade_commit
    entry=next(m for m in t if m.name.partition('/')[2]==policy_path)
    policy_data=t.extractfile(entry).read()
policy_file=source/'arcade'/policy_path;policy_file.parent.mkdir(parents=True);policy_file.write_bytes(policy_data)
arcade_warnings=[]
for node in E.fromstring(policy_data).iter():
    if node.tag.rsplit('}',1)[-1]=='When' and node.get('Condition')=="'$(Language)' == 'C#'":
        for item in node.iter():
            if item.tag.rsplit('}',1)[-1]=='NoWarn':arcade_warnings.extend(item.text.replace('$(NoWarn)','').strip(';').split(';'))
assert arcade_warnings==['1701','1702','1705','1591'],arcade_warnings
sdk_manifest=E.parse(source/'eng/Version.Details.xml').find(".//Dependency[@Name='Microsoft.DotNet.Arcade.Sdk']")
assert sdk_manifest.findtext('Sha')==arcade_commit and sdk_manifest.get('Version')=='1.0.0-beta.19101.13'
global_sdk=json.loads((source/'global.json').read_text())['msbuild-sdks']['Microsoft.DotNet.Arcade.Sdk']
assert global_sdk=='1.0.0-beta.19104.18'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
original=source/'src/Tasks/Microsoft.Build.Tasks.csproj';upstream=E.parse(original).getroot();upstream.attrib.pop('Sdk')
versions={'System.Collections.Immutable':'1.5.0','Microsoft.Win32.Registry':'4.3.0','Microsoft.Build.Framework':'16.0.461','Microsoft.Build.Utilities.Core':'16.0.461','System.CodeDom':'4.4.0','System.Reflection.Metadata':'1.6.0','System.Threading.Tasks.Dataflow':'4.6.0'}
pruned={'System.Linq.Parallel':'4.0.1','System.Net.Http':'4.3.0','System.Reflection.TypeExtensions':'4.1.0','System.Resources.Writer':'4.0.0'}
for group in upstream.findall('ItemGroup'):
    for item in list(group):
        if item.tag=='PackageReference' and item.get('Include') in pruned:group.remove(item)
resource_projections={}
for item in upstream.iter():
    if item.tag=='EmbeddedResource':
        relative=item.get('Include').replace('\\','/');original_resource=(original.parent/relative).resolve();assert original_resource.is_relative_to(source)
        raw=original_resource.read_bytes();projected=raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        destination=out/'windows-resource-inputs'/original_resource.relative_to(source);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(projected)
        resource_projections[str(original_resource.relative_to(source))]=dict(original_sha256=hashlib.sha256(raw).hexdigest(),Windows_CRLF_projection_sha256=hashlib.sha256(projected).hexdigest(),generated_path=str(destination.relative_to(out)))
        item.set('Include',native(destination))
    if item.tag=='Import':item.set('Project',native((original.parent/item.get('Project').replace('\\','/')).resolve()))
    if item.tag=='ProjectReference':
        name={'..\\Framework\\Microsoft.Build.Framework.csproj':'Microsoft.Build.Framework','..\\Utilities\\Microsoft.Build.Utilities.csproj':'Microsoft.Build.Utilities.Core'}[item.get('Include')];item.tag='PackageReference';item.set('Include',name);item.set('Version','[16.0.461]')
    elif item.tag=='PackageReference' and item.get('Include') in versions:item.set('Version','['+versions[item.get('Include')]+']')
    if item.tag in {'Compile','EmbeddedResource','None','Content'}:
        for attr in ['Include','Remove','Update']:
            if item.get(attr) and item.tag!='EmbeddedResource' and not item.get(attr).startswith(('$(', '@(')):item.set(attr,native(original.parent)+'/'+item.get(attr).replace('\\','/'))
E.indent(upstream);E.ElementTree(upstream).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
values=dict(TargetFramework='netstandard2.0',TargetFrameworkIdentifier='.NETStandard',TargetFrameworkVersion='v2.0',LibraryTargetFrameworks='netstandard2.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName='Microsoft.Build.Tasks.Core',RootNamespace='Microsoft.Build.Tasks',Configuration='Release',OsEnvironment='windows',DisableNerdbankVersioning='true',GenerateAssemblyInfo='false',GenerateDocumentationFile='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(source/'src/MSFT.snk'),TreatWarningsAsErrors='true',NuGetAudit='false',LangVersion='7.3',UseSharedCompilation='false',EnableNETAnalyzers='false',PackageId='Microsoft.Build.Tasks.Core',Version='16.0.461',PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/microsoft/msbuild',RepositoryCommit=commit)
values.update(AppendTargetFrameworkToOutputPath='false',OutputPath='bin/Release/',IntermediateOutputPath='obj/Release/')
warnings=[]
for file in [source/'Directory.Build.props',source/'src/Directory.Build.props']:
    for item in E.parse(file).iter():
        if item.tag.rsplit('}',1)[-1]=='NoWarn':warnings.append(item.text.replace('$(NoWarn)','').strip(';'))
values['NoWarn']=';'.join(warnings[:1]+[';'.join(arcade_warnings)]+warnings[1:])
for k,v in values.items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
E.SubElement(tree,'Import',Project='upstream.proj');E.SubElement(tree,'Import',Project=native(source/'src/Directory.BeforeCommon.targets'))
extra=E.SubElement(tree,'ItemGroup');E.SubElement(extra,'Compile',Include='BootstrapVersion.cs')
E.SubElement(extra,'None',Include=native(out/'bin/Release/netstandard2.0/Microsoft.Build.Tasks.Core.pdb'),Pack='true',PackagePath='lib/netstandard2.0/')
(out/'BootstrapVersion.cs').write_text('[assembly:System.Reflection.AssemblyVersion("15.1.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("16.0.461.62831")]\n[assembly:System.Reflection.AssemblyInformationalVersion("16.0.461+g6ff56ef63c")]\n[assembly:System.Reflection.AssemblyConfiguration("Release")]\n')
for license in ['LICENSE','THIRDPARTYNOTICES.txt']:E.SubElement(extra,'None',Include=native(source/license),Pack='true',PackagePath='/')
capture=E.SubElement(tree,'Target',Name='CaptureOriginalInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)policy.txt',Lines='$(TargetFramework)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)',Overwrite='true')
E.indent(tree);E.ElementTree(tree).write(out/'Tasks.csproj',encoding='utf-8',xml_declaration=True)
config='<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n'
(out/'NuGet.config').write_text(config)
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_file_sha256=hashes,production_CSharp_changes=0,original_frameworks=['net472','netstandard2.0'],compiled_framework='netstandard2.0',exact_original_dependency_versions=versions,original_Windows_resource_CRLF_projections=resource_projections,original_NS2_references_pruned_to_BCL=pruned,Arcade_policy_source_commit=arcade_commit,Arcade_policy_archive_sha256=hashlib.sha256(arcade.read_bytes()).hexdigest(),Arcade_policy_original_file=policy_path,Arcade_policy_original_file_sha256=hashlib.sha256(policy_data).hexdigest(),original_Arcade_CSharp_NoWarn=arcade_warnings,original_Arcade_version_in_global_json=global_sdk,original_Arcade_version_in_dependency_manifest=sdk_manifest.get('Version'),original_Arcade_version_manifest_discrepancy_resolved=False,pruning_API_and_runtime_identity_gate_required=True,NET472_profile_built=False,original_Nerdbank_toolchain_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original Tasks16 NS2 source/project imports and exact dependencies prepared')
