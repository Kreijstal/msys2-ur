"""Compare every selected original compiler/resource/policy input against the pinned SDK archive."""
from pathlib import Path
import hashlib,json,sys,tarfile
archive,plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=json.loads((plan/'source-inputs.json').read_text());source=Path(inputs['source_root']);records=json.loads((build/'results.json').read_text())['projects'];translations=json.loads((localized/'results.json').read_text())
assert sha(archive)==inputs['archive_sha256']=='3c9173ca31f070e662f705ebf6bc58c5a809fba78a407c3fb1f14274582ec85d'
wanted=dict(inputs['original_project_policy_sha256']);count=0
for r in records:
 wanted.update(r['original_source_sha256']);count+=len(r['original_source_sha256']);wanted.update({rel:v['sha256'] for rel,v in r['original_resources'].items()})
 for name,h in r['actual_reference_sha256'].items():assert sha(Path(name))==h,name
 for a in r['aliased_references']:assert sha(Path(a['path']))==a['sha256']
 for ext,h in r['output_sha256'].items():assert sha(build/'bin'/(r['assembly']+'.'+ext))==h
wanted.update(translations['original_xlf_sha256']);found={}
with tarfile.open(archive) as t:
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and rel in wanted:found[rel]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
assert set(found)==set(wanted)
for rel,h in wanted.items():assert sha(source/rel)==found[rel]==h,rel
for rel,h in translations['satellite_sha256'].items():assert sha(build/'bin'/rel)==h,rel
main=next(r for r in records if r['assembly']=='Microsoft.NET.Build.Tasks');assert [a['alias'] for a in main['aliased_references']]==['unused'];assert any(e['assembly']=='Microsoft.NET.Build.Extensions.Tasks' and e['metadata'].get('ReferenceOutputAssembly')=='false' for e in main['original_project_edges'])
assert count==299 and len(translations['satellite_sha256'])==78
out.write_text(json.dumps(dict(original_compile_items=count,unique_original_compile_inputs=len({p for r in records for p in r['original_source_sha256']}),archive_selected_inputs_verified=len(wanted),original_xlf_inputs=len(translations['original_xlf_sha256']),source_reference_output_and_satellite_hashes_verified=True,original_project_alias_and_build_only_edges_preserved=True,original_production_source_changes=0,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS299 original Compile items, selected source/resource/project/XLF bytes match pinned SDK archive; all reference/output/satellite hashes verified')
