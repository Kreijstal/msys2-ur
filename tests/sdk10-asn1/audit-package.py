"""Audit configuration archive bytes, original generator layout and retained strict API failure."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,snapshot,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-sdk10-asn1-bootstrap/';base='clang64/lib/dotnet10/library-packs/asn1-10.0.2-net10-bootstrap/bin/';manifest=json.loads(files[doc+'payload-sha256.json']);build=json.loads(files[doc+'build-results.json']);archives=json.loads(files[doc+'archives.json']);localization=json.loads(files[doc+'localization-results.json']);api=json.loads(files[doc+'api-results.json']);binary={}
for rel,h in manifest.items():assert sha(files['clang64/'+rel])==h,rel
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+p for p in manifest}|{doc+'payload-sha256.json'}
with tarfile.open(snapshot) as source:
 vmr=json.load(source.extractfile('source-inputs.json'));count=0
 for r in build['projects']:
  assert r['original_production_source_changes']==0
  for rel,h in {**r['original_source_sha256'],**r['original_resource_sha256']}.items():assert sha(source.extractfile('runtime/'+rel).read())==h==vmr['files'][rel]['sha256'],rel
  count+=len(r['original_source_sha256'])
  for ext,h in r['output_sha256'].items():binary[r['assembly']+'.'+ext]=h

assert count==41 and len(build['projects'])==1
binary.update(localization['satellite_sha256']);assert {n[len(base):] for n in files if n.startswith(base)}==set(binary)
for rel,h in binary.items():assert sha(files[base+rel])==h,rel
for assembly,a in archives.items():
 data=files['clang64/'+a['archive']];assert sha(data)==a['sha256']
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert sha(z.read(member))==h,member
  md=E.fromstring(z.read(assembly+'.nuspec')).find('metadata');assert md.findtext('id')==assembly and md.findtext('version')=='10.0.2'
  assert md.find('repository').get('commit')=='44525024595742ebe09023abe709df51de65009b';assert md.find('dependencies/group').get('targetFramework')=='net10.0'
  record=next(r for r in build['projects'] if r['assembly']==assembly)
  for ext,h in record['output_sha256'].items():assert sha(z.read('lib/net10.0/'+assembly+'.'+ext))==h
assert len(archives)==1 and all(p['exit_code']==0 and p['comparison']['total_differences']==0 and not p['comparison']['nullable_annotation_differences'] for p in api['projects'].values())
assert sum(p['comparison']['expected_entries'] for p in api['projects'].values())==218
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_VMR_files_verified=len(vmr['files']),original_compile_inputs=41,source_binary_symbol_documentation_assets=len(binary),source_archive_sha256=sha(snapshot.read_bytes()),original_NET10_Asn1_archive_verified=True,original_production_source_changes=0,CLR_declarations_checked=218,strict_CLR_and_nullable_contract_gate_passed=True,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
