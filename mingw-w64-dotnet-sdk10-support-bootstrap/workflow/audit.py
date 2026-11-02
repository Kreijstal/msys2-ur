"""Verify the actual selected source inputs against the immutable VMR source view."""
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve();snapshot=root/'plan/snapshot';source=snapshot/'runtime';manifest=json.loads((snapshot/'snapshot-sha256.json').read_text());vmr=json.loads((snapshot/'vmr-source-inputs.json').read_text());build=json.loads((root/'build/results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,h in manifest.items():assert sha(snapshot/rel)==h,rel
count=0
for record in build['projects']:
    for kind in ['original_source_sha256','original_resource_sha256']:
        for rel,h in record[kind].items():
            assert sha(source/rel)==h and manifest['runtime/'+rel]==h,rel
            assert vmr['original_vmr_files'][rel]['sha256']==h,rel
    count+=len(record['original_source_sha256'])
    for rel,h in record['original_reference_sha256'].items():assert sha(Path(rel))==h,rel
    for ext,h in record['output_sha256'].items():assert sha(root/'build/bin'/(record['assembly']+'.'+ext))==h
assert count==133
assert not list((source/'src/libraries/System.IO.Hashing/src/Resources').rglob('*.xlf'))
assert not list((source/'src/libraries/Microsoft.Extensions.DependencyModel/src/Resources').rglob('*.xlf'))
(root/'source-audit.json').write_text(json.dumps(dict(original_vmr_compile_inputs=count,vmr_source_files_verified=len(vmr['original_vmr_files']),snapshot_inputs_verified=len(manifest),all_original_vmr_selected_source_resource_reference_and_output_hashes_match=True,original_xlf_inputs=0,original_production_source_changes=0,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS133 original VMR compiler inputs,exact snapshot/reference/output hashes and original no-XLF resource profile')
