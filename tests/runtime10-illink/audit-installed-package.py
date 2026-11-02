"""Compare every installed ILLink10 bootstrap byte and actual normalized PE versions."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folder=prepared/'illink/bin/Release/net8.0';prefix='clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/'
expected={prefix+p.name:p for p in folder.glob('*.dll')};assert len(expected)==7
for name in ['illink.deps.json','illink.runtimeconfig.json']:expected[prefix+name]=folder/name
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
 for m in t:
  if m.isdir() or m.name.startswith('.'):continue
  assert m.isfile() and (m.name in expected or m.name=='clang64/bin/illink10-bootstrap' or m.name.startswith(('clang64/share/doc/dotnet-illink10-bootstrap/','clang64/share/licenses/dotnet-illink10-bootstrap/'))),m.name
  data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
  if m.name in expected:assert data==expected[m.name].read_bytes(),m.name
  files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==21 and set(expected)<=set(files),len(files)
version_record=json.loads((folder/'illink.deps.json.version-metadata.json').read_text());deps=json.loads(Path('/clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/illink.deps.json').read_text());target=deps['targets'][deps['runtimeTarget']['name']]
for item in version_record:
 actual=target[item['library']]['runtime'][item['asset']]
 assert actual['assemblyVersion']==item['actual_assembly_version'] and actual['fileVersion']==item['actual_file_version'],item
result=dict(formal_pacman_installed=True,package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_source_tool_and_dependency_assemblies_verified=7,normalized_actual_pe_dependency_entries_verified=len(version_record),installed_files_sha256=files,original_net10_host_built=False,illink_tasks_package_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(result,indent=2)+'\n');print('PASS 21 installed ILLink/bootstrap files, seven exact source assemblies and actual normalized dependency versions')
