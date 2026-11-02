"""Verify every source snapshot file and all original compiler/reference/resource/output hashes."""
from pathlib import Path
import hashlib, json, sys, tarfile

archive, plan, build, localized, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == 'f688556c4895b4e484b0a17d0291947a6d6dfc7dc482dcbda3d4368399ab9f05'
inputs = json.loads((plan / 'source-inputs.json').read_text())
source = Path(inputs['source_root'])
manifest = inputs['source_manifest']
assert len(manifest['files']) == 4418
seen = set()
with tarfile.open(archive, 'r|gz') as t:
    for m in t:
        if m.isfile() and m.name.startswith('runtime/'):
            rel = m.name[len('runtime/'):]
            assert rel not in seen
            seen.add(rel)
            assert hashlib.sha256(t.extractfile(m).read()).hexdigest() == sha(source / rel) == manifest['files'][rel]['sha256'], rel
assert seen == set(manifest['files'])
records = json.loads((build / 'results.json').read_text())['projects']
assert len(records) == 1
record = records[0]
assert record['original_framework'] == 'net8.0' and record['version'] == '8.0.1'
assert record['assembly_version'] == '8.0.0.0' and record['file_version'] == '8.0.724.31311'
assert record['original_production_source_changes'] == 0 and record['public_key_token'] == 'cc7b13ffcd2ddd51'
for rel, h in {**record['original_source_sha256'], **record['original_resource_sha256'], **inputs['original_projects_and_properties']}.items():
    assert sha(source / rel) == h == manifest['files'][rel]['sha256'], rel
for path, h in {**record['original_reference_sha256'], **record['generated_source_sha256']}.items():
    assert sha(Path(path)) == h, path
assert len(record['original_reference_sha256']) == 162
for ext, h in record['output_sha256'].items():
    assert sha(build / 'bin' / ('System.Formats.Asn1.' + ext)) == h
documentation = record['original_documentation']
assert documentation['archive_sha256'] == '48b7ad1dedcdcd36143c1b8611f6f8d185024b253781695b0afb06133449139a'
assert sha(build / 'bin/System.Formats.Asn1.xml') == documentation['sha256']
translations = json.loads((localized / 'results.json').read_text())
for rel, h in translations['original_xlf_sha256'].items():
    assert sha(source / rel) == h == manifest['files'][rel]['sha256']
for rel, h in translations['satellite_sha256'].items():
    assert sha(build / 'bin' / rel) == h
rsp = (build / 'System.Formats.Asn1/compile.rsp').read_text()
assert '/nostdlib+\n' in rsp and '/warnaserror+\n' in rsp
assert '/features:strict,nullablePublicOnly\n' in rsp
out.write_text(json.dumps(dict(original_snapshot_files_verified=4418,
    original_compile_inputs=len(record['original_source_sha256']), original_source_changes=0,
    original_NET8_profile_and_incremental_servicing_version_preserved=True,
    all_source_reference_generated_resource_output_and_satellite_hashes_verified=True,
    original_framework_reference_pack='8.0.31', original_Arcade_build_id='20240613.11',
    other_original_framework_profiles_built=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS 4418 original source files, NET8 compiler inputs, references, resources and produced asset hashes')
