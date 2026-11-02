"""Extract CodeDom's exact source and prepare its original NET9 evaluation."""
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
  if n.startswith('src/libraries/System.CodeDom/') and p.suffix in {'.resx','.xlf','.xliff','.resources'}:resource_members.append(n)
  if not (n.startswith(('src/libraries/System.CodeDom/','src/libraries/Common/')) or n in {'src/libraries/Directory.Build.targets','src/libraries/Directory.Build.props','src/libraries/NetCoreAppLibrary.props','eng/Versions.props','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'}):continue
  if 'tests' in p.parts or 'test' in p.parts:continue
  data=t.extractfile(m).read()
  if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.res','.resources'} or data.startswith(b'MZ'):removed.append(n);continue
  f=source/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data);extracted[n]=hashlib.sha256(data).hexdigest()
assert resource_members==['src/libraries/System.CodeDom/src/Resources/Strings.resx'],resource_members
version_file=prefix/'share/doc/dotnet-reference9-servicing/version-build-inputs.json';version=json.loads(version_file.read_text());assert version['arcade_source_commit']=='6666973b629b24e259162dba03486c23af464bab' and version['version_prefix']=='9.0.11' and version['upstream_task_vectors_checked']==3
(out/'file-version.txt').write_text(version['file_version']+'\n');(out/'version-build-inputs.json').write_text(json.dumps(version,indent=2)+'\n')
subprocess.run([sys.executable,'-X','utf8',str(here/'prepare-codedom.py'),str(source),str(out/'plan')],check=True)
tool=out/'evaluation-tool';tool.mkdir();tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',UseSharedCompilation='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include=(here/'codedom-inputs/EvaluateProjects.cs').as_posix())
for n in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:E.SubElement(E.SubElement(items,'Reference',Include=n),'HintPath').text=(prefix/'lib/dotnet/sdk/8.0.131'/(n+'.dll')).as_posix()
E.ElementTree(tree).write(tool/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out/'extraction.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive),source_commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57',removed_binary_inputs=removed,extracted_source_sha256=extracted,original_resource_members=resource_members,localized_source_resources_present=False,version_policy_document_sha256=sha(version_file),original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('Prepared source CodeDom9 NET9;all original resources accounted for')

subprocess.run([sys.executable,"-X","utf8",str(here/"add-documentation.py"),str(out),str(documentation)],check=True)
