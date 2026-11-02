"""Audit final package bytes against original core source and compiler-output records."""
from pathlib import Path
import hashlib, json, sys, tarfile

artifact, snapshot, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes()) == '45e8453e4868b201f8dda3214931cce9ebfd965272c8e7972e49c56291d05106'
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-reference6-core-bootstrap/'
pack = 'clang64/lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap/'
manifest = json.loads(files[doc + 'payload-sha256.json'])
for rel, h in manifest.items():
    assert sha(files['clang64/' + rel]) == h, rel
assert {n for n in files if n.startswith('clang64/')} == {'clang64/' + n for n in manifest} | {doc + 'payload-sha256.json'}
build = json.loads(files[pack + 'build/results.json'])
assert len(build['projects']) == 137 and not build['complete_targeting_pack_built']
with tarfile.open(snapshot) as t:
    source = json.load(t.extractfile('source-inputs.json'))
    count = 0
    for name, record in build['projects'].items():
        assert record['original_production_source_changes'] == 0 and record['exit_code'] == 0
        assert sha(files[pack + 'build/ref/net6.0/' + name + '.dll']) == record['output_sha256']
        for rel, h in record['original_sources'].items():
            assert sha(t.extractfile('runtime/' + rel).read()) == h == source['files'][rel]
            count += 1
assert count == 167
assert len([n for n in files if n.startswith(pack + 'build/ref/net6.0/')]) == 137
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()), payload_files=len(manifest),
    original_core_reference_assemblies=137, original_compile_inputs=167, original_source_changes=0,
    original_source_and_reference_payload_hashes_verified=True, compatibility_facades_built=False,
    complete_targeting_pack_built=False, full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
