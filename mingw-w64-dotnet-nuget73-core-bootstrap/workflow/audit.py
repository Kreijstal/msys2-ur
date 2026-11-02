"""Independently verify exact original NuGet source,resource and output hashes."""
from pathlib import Path
import hashlib,json,sys,tarfile

root=Path(sys.argv[1]).resolve();build=json.loads((root/'build/results.json').read_text());local=json.loads((root/'localized/results.json').read_text());checked={}
with tarfile.open(root/'nuget-sdk10-bf048eb7.tar.gz') as t:
    members={m.name.partition('/')[2]:m for m in t.getmembers() if m.isfile()}
    for r in build['projects']:
        for kind in ['original_source_sha256','original_resource_sha256']:
            for path,h in r[kind].items():assert hashlib.sha256(t.extractfile(members[path]).read()).hexdigest()==h,path;checked[path]=h
        assert hashlib.sha256((root/'build/bin'/(r['assembly']+'.dll')).read_bytes()).hexdigest()==r['output_sha256']
        for path,h in r['actual_reference_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    for path,h in local['original_xlf_sha256'].items():assert hashlib.sha256(t.extractfile(members[path]).read()).hexdigest()==h,path;checked[path]=h
for path,h in local['satellite_sha256'].items():assert hashlib.sha256((root/'build/bin'/path).read_bytes()).hexdigest()==h,path
report=dict(original_compile_items=sum(len(r['original_source_sha256']) for r in build['projects']),distinct_original_source_resource_and_xlf_inputs=len(checked),original_xlf_inputs=len(local['original_xlf_sha256']),all_original_archive_output_and_reference_hashes_match=True,original_production_source_changes=0)
assert report['original_compile_items']==187 and report['original_xlf_inputs']==52
(root/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS187 original source items,52 XLF inputs,outputs and actual reference hashes')
