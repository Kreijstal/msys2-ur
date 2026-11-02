from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve();source=root/'source';origin=json.loads((source/'source-inputs.json').read_text());refs=json.loads((root/'references/results.json').read_text());build=json.loads((root/'build/results.json').read_text());local=json.loads((root/'localized/results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,r in origin['files'].items():assert sha(source/rel)==r['sha256'],rel
for record in refs['projects']:
    for rel,h in record['original_source_sha256'].items():assert sha(source/rel)==h,rel
    for path,h in record['actual_reference_sha256'].items():assert sha(Path(path))==h,path
    assert sha(Path(record['output']))==record['output_sha256']
for rel,h in build['original_source_sha256'].items():assert sha(source/rel)==h,rel
for path,h in build['actual_reference_sha256'].items():assert sha(Path(path))==h,path
for ext,h in build['output_sha256'].items():assert sha(root/'build'/('Microsoft.Deployment.DotNet.Releases.'+ext))==h
for rel,h in local['original_xlf_sha256'].items():assert sha(source/'src/deployment-tools'/rel)==h,rel
for rel,h in local['satellite_sha256'].items():assert sha(root/'build'/rel)==h
assert len(refs['projects'])==9 and len(build['original_source_sha256'])==15 and len(local['satellite_sha256'])==13
(root/'source-audit.json').write_text(json.dumps(dict(original_vmr_source_files=len(origin['files']),original_production_cs_inputs=15,original_reference_assemblies=9,original_reference_cs_inputs=sum(len(r['original_source_sha256']) for r in refs['projects']),original_xlf_inputs=13,localized_resource_values=local['localized_values'],all_original_source_reference_and_output_bytes_match=True,original_framework='netstandard2.0',original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original NS2 Releases,9 exact reference assemblies and13 source XLF satellites')
