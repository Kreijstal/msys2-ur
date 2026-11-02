"""Verify the exact VMR source snapshot,original profiles and all compiler/resource outputs."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();origin=json.loads((plan/'snapshot/vmr-source-inputs.json').read_text());source=plan/'snapshot/command-line-api';records=json.loads((build/'results.json').read_text());translations=json.loads((localized/'results.json').read_text());files={}
with tarfile.open(archive) as t:
 for m in t:
  if m.isfile():files[m.name]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
for rel,r in origin['files'].items():
 data=(source/rel).read_bytes();assert sha(source/rel)==files['command-line-api/'+rel]==r['sha256'];assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==r['git_blob_sha1']
for record in records['projects']:
 tfm=record['original_target'];assert len(record['original_source_sha256'])==74
 for rel,h in record['original_source_sha256'].items():assert h==origin['files'][rel]['sha256'] and sha(source/rel)==h,rel
 for rel,h in record['original_resource_sha256'].items():assert h==origin['files'][rel]['sha256'],rel
 for rel,h in record['actual_reference_sha256'].items():assert sha(Path(rel))==h,rel
 for ext,h in record['output_sha256'].items():assert sha(build/tfm/'bin'/('System.CommandLine.'+ext))==h
for rel,h in translations['original_xlf_sha256'].items():assert h==origin['files'][rel]['sha256'],rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/rel)==h,rel
assert set(r['original_target'] for r in records['projects'])=={'net10.0','netstandard2.0'} and len(translations['satellite_sha256'])==28
out.write_text(json.dumps(dict(exact_vmr_files_verified=len(origin['files']),original_compile_items_per_framework=74,original_frameworks=['net10.0','netstandard2.0'],original_xlf_inputs=14,satellites=28,all_source_policy_resource_reference_output_hashes_match=True,original_production_source_changes=0,full_original_framework_runtime_dependency_closure=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS405 exact VMR files,74 original compile items per profile,28 satellites and all reference/output hashes')
