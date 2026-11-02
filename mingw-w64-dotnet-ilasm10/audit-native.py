"""Verify native sources against archive bytes and replayed patches on Windows."""
from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile

mode, archive_name, root_name, workflow_name = sys.argv[1:]
archive, root, here = map(Path, [archive_name, root_name, workflow_name])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
record=json.loads((root/'source-inputs.json').read_text())
patches=['host-mingw.patch','coreclr-mingw.patch','resource-section-index.patch','cetcompat.patch']
changed=set()
for name in patches:
    changed.update(re.findall(r'^\+\+\+ b/(.+)$',(here/name).read_text(),re.M))
replay=root/'audit-replay'
if mode=='prepare':
    assert not replay.exists()
    replay.mkdir()
    verified=set()
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment']==record['runtime_source_commit']
        for m in t:
            name=m.name.partition('/')[2]
            if not (m.isfile() or m.issym()):continue
            if name in record['original_file_sha256'] or name in changed:
                data=t.extractfile(m).read()
                if name in record['original_file_sha256']:
                    assert hashlib.sha256(data).hexdigest()==record['original_file_sha256'][name],name
                    verified.add(name)
                if name in changed:
                    p=replay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    assert verified==set(record['original_file_sha256'])
    for name in changed:(replay/name).parent.mkdir(parents=True,exist_ok=True)
    (root/'archive-audit.json').write_text(json.dumps(dict(original_archive_files_verified=len(verified),patch_paths=sorted(changed)),indent=2)+'\n')
elif mode=='verify':
    assert replay.is_dir()
    for name,digest in record['original_file_sha256'].items():
        expected=sha(replay/name) if name in changed else digest
        assert sha(root/'r'/name)==expected,name
    for name in changed:assert (replay/name).read_bytes()==(root/'r'/name).read_bytes(),name
    for p,digest in json.loads((root/'native-version-inputs.json').read_text())['generated_header_sha256'].items():
        assert sha(root/p)==digest,p
    commands=json.loads((root/'coreclr-build/compile_commands.json').read_text())
    sources=[]
    for item in commands:
        if item.get('output','').replace('\\','/').startswith('ilasm/') or '/ilasm/' in item['file'].replace('\\','/'):
            p=Path(item['file']);assert p.is_relative_to(root/'r'),p
            relative=p.relative_to(root/'r').as_posix()
            assert relative in record['original_file_sha256'] or relative in changed,relative
            sources.append(relative)
    assert len(sources)>=8,sources
    report=dict(original_archive_files_verified=len(record['original_file_sha256']),replayed_source_patch_paths_verified=len(changed),
                actual_ilasm_compilation_units_verified=len(sources),actual_ilasm_sources=sorted(set(sources)),
                native_version_headers_verified=True,production_unsafe_il_changes=0,
                only_ilasm_target_built=True,full_runtime10_complete=False,full_dependency_goal_complete=False)
    (root/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native source archive, exact patch replay, generated versions and actual ILAsm compile inputs')
else:raise ValueError(mode)
