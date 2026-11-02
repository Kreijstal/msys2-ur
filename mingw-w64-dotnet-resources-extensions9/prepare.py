"""Extract ResourcesExtensions's exact source and prepare its original NET9 evaluation."""
from pathlib import Path,PurePosixPath
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out,documentation=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir(parents=True);here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(archive)=='63ab12fafdec8559d59d25e21ddaf0edbde90d6c538b44d4cbb6f693a61e90df'
source=out/'r';source.mkdir();removed=[];extracted={};resource_members=[]
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='fa7cdded37981a97cec9a3e233c4a6af58a91c57'
 for m in t:
  if not m.isfile():continue
  n=m.name.partition('/')[2];p=PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts
  if n.startswith('src/libraries/System.Resources.Extensions/src/') and p.suffix in {'.resx','.xlf','.xliff','.resources'}:resource_members.append(n)
  if not (n.startswith(('src/libraries/System.Resources.Extensions/','src/libraries/Common/','src/libraries/System.Private.CoreLib/src/')) or n in {'src/libraries/Directory.Build.targets','src/libraries/Directory.Build.props','src/libraries/NetCoreAppLibrary.props','eng/Versions.props','eng/intellisense.targets','Directory.Build.props','global.json','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'}):continue
  if 'tests' in p.parts or 'test' in p.parts:continue
  data=t.extractfile(m).read()
  if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.res','.resources'} or data.startswith(b'MZ'):removed.append(n);continue
  f=source/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data);extracted[n]=hashlib.sha256(data).hexdigest()
assert resource_members==['src/libraries/System.Resources.Extensions/src/Resources/Strings.resx'],resource_members
versions=E.parse(source/'eng/Versions.props');project=E.parse(source/'src/libraries/System.Resources.Extensions/src/System.Resources.Extensions.csproj')
assert versions.findtext('.//PreReleaseVersionLabel')=='servicing' and project.findtext('.//IsPackable')=='true'
assert 'System.Resources.Extensions;' in E.parse(source/'src/libraries/NetCoreAppLibrary.props').findtext('.//WindowsDesktopCoreAppLibrary')
assembly_version='.'.join([versions.findtext('.//MajorVersion'),versions.findtext('.//MinorVersion'),'0','0']);assert assembly_version=='9.0.0.0'
(out/'assembly-version-policy.json').write_text(json.dumps(dict(original_assembly_version=assembly_version,source='Original servicing targeting-pack assembly-version rule in src/libraries/Directory.Build.targets',in_runtime_or_desktop_targeting_pack=True),indent=2)+'\n')
dependencies=out/'dependencies';dependencies.mkdir()
import zipfile
nrbf_package=prefix/'lib/dotnet/library-packs/system.formats.nrbf.9.0.11.nupkg'
with zipfile.ZipFile(nrbf_package) as z:(dependencies/'System.Formats.Nrbf.dll').write_bytes(z.read('lib/net9.0/System.Formats.Nrbf.dll'))
(out/'dependency-inputs.json').write_text(json.dumps(dict(source_nrbf_nuget_sha256=sha(nrbf_package),source_nrbf_dll_sha256=sha(dependencies/'System.Formats.Nrbf.dll'),original_version='9.0.11'),indent=2)+'\n')
assert sha(documentation)=='227bc364165d241eeb122e410216e9cbdb955400402475477c506e7ce8c4117c'
assert versions.findtext('.//MicrosoftPrivateIntellisenseVersion')=='9.0.0-preview-20241010.1'
assert project.findtext('.//UseCompilerGeneratedDocXmlFile')=='false'
member='IntellisenseFiles/net/1033/System.Resources.Extensions.xml'
with zipfile.ZipFile(documentation) as z:
 for n in z.namelist():
  if n.endswith('/'):continue
  data=z.read(n);assert not n.lower().endswith(('.dll','.exe','.so','.dylib','.winmd')) and not data.startswith(b'MZ'),n
 xml=z.read(member)
 assert E.fromstring(xml).findtext('./assembly/name')=='System.Resources.Extensions'
doc_dir=out/'documentation';doc_dir.mkdir();(doc_dir/'System.Resources.Extensions.xml').write_bytes(xml)
(out/'documentation-inputs.json').write_text(json.dumps(dict(package_id='Microsoft.Private.Intellisense',version='9.0.0-preview-20241010.1',package_sha256=sha(documentation),member=member,xml_sha256=hashlib.sha256(xml).hexdigest(),original_intellisense_policy=True,no_implementation_binaries_in_documentation_package=True),indent=2)+'\n')
sdk=json.loads((source/'global.json').read_text())['sdk']['version'];assert sdk=='9.0.111'
(out/'language-build-policy.json').write_text(json.dumps(dict(original_sdk=sdk,original_language_setting='preview',bootstrap_compiler='source Roslyn5.3',bootstrap_language='13.0',original_preview_toolchain_verified=False),indent=2)+'\n')
version_file=prefix/'share/doc/dotnet-reference9-servicing/version-build-inputs.json';version=json.loads(version_file.read_text());assert version['arcade_source_commit']=='6666973b629b24e259162dba03486c23af464bab' and version['version_prefix']=='9.0.11' and version['upstream_task_vectors_checked']==3
(out/'file-version.txt').write_text(version['file_version']+'\n');(out/'version-build-inputs.json').write_text(json.dumps(version,indent=2)+'\n')
subprocess.run([sys.executable,'-X','utf8',str(here/'prepare-library.py'),str(source),str(out/'plan')],check=True)
tool=out/'evaluation-tool';tool.mkdir();tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',UseSharedCompilation='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include=(here/'inputs/EvaluateProjects.cs').as_posix())
for n in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:E.SubElement(E.SubElement(items,'Reference',Include=n),'HintPath').text=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix()
E.ElementTree(tree).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out/'extraction.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive),source_commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57',removed_binary_inputs=removed,extracted_source_sha256=extracted,original_resource_members=resource_members,localized_source_resources_present=False,version_policy_document_sha256=sha(version_file),original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('Prepared source ResourcesExtensions9 NET9;all original resources accounted for')
