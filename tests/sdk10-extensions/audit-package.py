"""Audit package provenance and retain the failed strict nullable gate explicitly."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,zipfile
artifact,snapshot,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-sdk10-logging-abstractions-bootstrap/';manifest=json.loads(files[doc+'payload-sha256.json']);build=json.loads(files[doc+'build-results.json']);archives=json.loads(files[doc+'archives.json']);api=json.loads(files[doc+'api-baseline-results.json'])
for rel,h in manifest.items():assert sha(files['clang64/'+rel])==h,rel
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+p for p in manifest}|{doc+'payload-sha256.json'}
with tarfile.open(snapshot) as source:
 vmr=json.load(source.extractfile('source-inputs.json'))
 count=0
 for r in build['projects']:
  for rel,h in r['original_source_sha256'].items():assert sha(source.extractfile('runtime/'+rel).read())==h==vmr['files'][rel]['sha256'],rel
  count+=len(r['original_source_sha256'])
  for ext,h in r['output_sha256'].items():assert sha(files['clang64/lib/dotnet10/library-packs/logging-abstractions-10.0.2-net10-bootstrap/bin/'+r['assembly']+'.'+ext])==h
assert count==74 and len(build['projects'])==3
for assembly,a in archives.items():
 data=files['clang64/'+a['archive']];assert sha(data)==a['sha256']
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert sha(z.read(member))==h,member
assert len(archives)==2 and api['CLR_contract_entries']==404 and api['CLR_missing_extra_changed']==0
assert api['strict_DI_nullable_contract_gate_exit_code']==1 and api['strict_DI_nullable_contract_gate_passed'] is False and api['original_DI_nullable_discrepancies']==25
r=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_VMR_files_verified=len(vmr['files']),original_compile_items=74,original_profiles=['net10.0','netstandard2.0'],two_source_archives_verified=True,source_archive_sha256=sha(snapshot.read_bytes()),CLR_contract_entries=404,CLR_missing_extra_changed=0,strict_DI_nullable_contract_gate_exit_code=1,strict_DI_nullable_contract_gate_passed=False,original_DI_nullable_discrepancies=25,full_logging_console_graph_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
