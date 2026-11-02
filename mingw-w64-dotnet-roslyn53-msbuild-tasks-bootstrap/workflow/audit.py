"""Independently compare selected cold inputs with original pinned archives."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile

root=Path(sys.argv[1]).resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report={}
for label,archive,records in [
 ('msbuild17',root/'msbuild-17.11.48-02bf6629.tar.gz',json.loads((root/'msbuild17/results.json').read_text())['projects']),
 ('roslyn_task',root/'roslyn-sdk10-2333221c.tar.gz',[json.loads((root/'task/results.json').read_text())])]:
    checked={}
    with tarfile.open(archive) as t:
        members={m.name.partition('/')[2]:m for m in t.getmembers() if m.isfile()}
        def verify(path,digest):
            assert hashlib.sha256(t.extractfile(members[path]).read()).hexdigest()==digest,path
            checked[path]=digest
        for r in records:
            for k in ['original_source_sha256','original_resource_sha256']:
                for path,digest in r[k].items():verify(path,digest)
            for path,digest in r['actual_reference_sha256'].items():assert sha(Path(path))==digest,path
            base=root/'msbuild17'/r['project'] if 'project' in r else root/'task'
            dll=base/((r['project'] if 'project' in r else 'Microsoft.Build.Tasks.CodeAnalysis')+'.dll');assert sha(dll)==r['output_sha256']
        if label=='roslyn_task':
            for path,digest in json.loads((root/'task-plan/source-inputs.json').read_text())['original_project_inputs_sha256'].items():verify(path,digest)
            for path,digest in json.loads((root/'localized/results.json').read_text())['original_xlf_sha256'].items():verify(path,digest)
    report[label]=dict(original_compile_items=sum(len(r['original_source_sha256']) for r in records),distinct_archive_inputs=len(checked),all_original_input_output_reference_hashes_match=True)
package=root/'microsoft.codeanalysis.collections.4.2.0-1.22102.8.nupkg';assert sha(package)=='854de69d3c5f2a92e06757d48dc136e9fa7887814a999917dc689733ee2431a8'
r=json.loads((root/'msbuild17/Microsoft.Build.Framework/results.json').read_text())
with zipfile.ZipFile(package) as z:
    for name,digest in r['source_package_cs_sha256'].items():assert hashlib.sha256(z.read(name.partition('/')[2])).hexdigest()==digest
report['collections_source_items']=len(r['source_package_cs_sha256']);assert report['collections_source_items']==37
assert report['msbuild17']['original_compile_items']==1195 and report['roslyn_task']['original_compile_items']==60
(root/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS cold source/archive/reference/output audit:1195 MSBuild17 items,37 Collections items,60 NET10 task items and13 XLF inputs')
