"""Independently match compiled NET6 inputs to the pinned archive and own reference graph."""
from pathlib import Path
import hashlib, json, sys, tarfile

archive, plan, build, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '45e8453e4868b201f8dda3214931cce9ebfd965272c8e7972e49c56291d05106'
inputs = json.loads((plan / 'source-inputs.json').read_text())
source = Path(inputs['source_root'])
manifest = inputs['source_manifest']
records = json.loads((build / 'results.json').read_text())['projects']
model = json.loads((plan / 'evaluated.json').read_text())
assert set(records) == set(inputs['public_core_contracts']) == set(model) and len(records) == 137
assert len(manifest['files']) == 4480
seen = set()
with tarfile.open(archive, 'r|gz') as t:
    for member in t:
        if member.isfile() and member.name.startswith('runtime/'):
            rel = member.name[len('runtime/'):]
            assert rel not in seen
            seen.add(rel)
            assert hashlib.sha256(t.extractfile(member).read()).hexdigest() == sha(source / rel) == manifest['files'][rel], rel
assert seen == set(manifest['files'])
compiled = set()
items = 0
for name, r in records.items():
    assert r['exit_code'] == 0 and r['framework'] == 'net6.0' and r['original_production_source_changes'] == 0
    originals = {Path(p['full_path']).relative_to(source).as_posix() for p in model[name]['items']['Compile']}
    assert set(r['original_sources']) == originals
    for rel, h in r['original_sources'].items():
        assert sha(source / rel) == h == manifest['files'][rel]
        compiled.add(rel)
    items += len(originals)
    folder = build / 'projects' / name
    rsp = (folder / 'compile.rsp').read_text()
    assert sha(folder / 'compile.rsp') == r['response_sha256']
    assert sha(folder / 'AssemblyInfo.cs') == r['assembly_info_sha256']
    assert '/nostdlib+\n' in rsp and '/refonly\n' in rsp
    if model[name]['properties']['TreatWarningsAsErrors'].lower() == 'true':
        assert '/warnaserror+\n' in rsp
    references = [line[len('/reference:"'):-1] for line in rsp.splitlines() if line.startswith('/reference:"')]
    assert {Path(p).name for p in references} == set(r['dependency_sha256'])
    for path in references:
        ref = Path(path)
        assert ref.parent == build / 'ref/net6.0'
        assert sha(ref) == r['dependency_sha256'][ref.name]
    assert sha(build / 'ref/net6.0' / (name + '.dll')) == r['output_sha256']
assert items == 167
report = dict(original_snapshot_files_verified=4480, original_core_contract_projects=137,
    original_compile_items=167, unique_original_compile_files=len(compiled),
    all_source_reference_and_output_hashes_verified=True, compiler_inputs_use_only_own_NET6_contract_graph=True,
    original_framework_and_warnings_as_errors_preserved=True, original_production_source_changes=0,
    compatibility_facades_built=False, complete_targeting_pack_built=False,
    full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print('PASS 4480 original files, 167 compiler items, own NET6 references and all output hashes')
