"""Verify both producers against the exact source archive and validated NET6 reference graph."""
from pathlib import Path
import hashlib, json, sys, tarfile

archive, plan, build, reference_root, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == 'b7966d5ca8035410adc673fa1f359ed973de0b70714d7db68e8172d06afc988f'
inputs = json.loads((plan / 'source-inputs.json').read_text())
source = Path(inputs['source_root'])
manifest = inputs['source_manifest']
assert len(manifest['files']) == 3968
seen = set()
archive_manifest = None
with tarfile.open(archive, 'r|gz') as t:
    for m in t:
        if not m.isfile():
            continue
        if m.name == 'source-inputs.json':
            archive_manifest = json.load(t.extractfile(m))
        elif m.name.startswith('runtime/'):
            rel = m.name[len('runtime/'):]
            assert rel not in seen
            seen.add(rel)
            assert hashlib.sha256(t.extractfile(m).read()).hexdigest() == sha(source / rel) == manifest['files'][rel]['sha256'], rel
assert archive_manifest == manifest and seen == set(manifest['files'])
records = json.loads((build / 'results.json').read_text())['projects']
assert set(records) == {'windows', 'portable'}
source_items = 0
xml = set()
for label, record in records.items():
    assert record['original_production_source_changes'] == 0
    assert record['framework'] == ('net6.0-windows' if label == 'windows' else 'net6.0')
    for rel, h in {**record['original_source_sha256'], **record['original_resource_sha256']}.items():
        assert sha(source / rel) == h == manifest['files'][rel]['sha256']
    for rel, item in record['original_AsnXml_regeneration'].items():
        assert sha(source / rel) == item['xml_sha256']
        assert sha(Path(str(source / rel) + '.cs')) == item['checked_in_cs_sha256']
        xml.add(rel)
    assert record['original_AsnXml_outputs_match_ignoring_only_line_endings']
    assert len(record['source_NET6_reference_sha256']) == 137
    for name, h in record['source_NET6_reference_sha256'].items():
        assert sha(reference_root / 'build/ref/net6.0' / name) == h
    for ext, h in record['output_sha256'].items():
        assert sha(build / label / 'bin' / ('System.Security.Cryptography.Pkcs.' + ext)) == h
    for p, h in record['generated_source_sha256'].items():
        assert sha(Path(p)) == h
    rsp = (build / label / 'compile.rsp').read_text()
    assert '/nostdlib+\n' in rsp and '/warnaserror+\n' in rsp
    source_items += len(record['original_source_sha256'])
assert source_items == 393 and len(xml) == 59
resources = [rel for rel in manifest['files'] if rel.startswith('src/libraries/System.Security.Cryptography.Pkcs/src/Resources/')]
assert resources == ['src/libraries/System.Security.Cryptography.Pkcs/src/Resources/Strings.resx']
report = dict(original_snapshot_files_verified=3968, original_profile_compile_items=393,
    original_NET6_Windows_compile_items=241, original_NET6_portable_compile_items=152,
    unique_original_AsnXml_inputs_regenerated_per_profile=59, original_production_source_changes=0,
    original_source_and_own_NET6_reference_and_output_hashes_verified=True,
    original_resource_files=resources, original_XLF_files=0, localized_satellite_assemblies_required=0,
    formal_package_built=False, other_original_framework_profiles_built=False, full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print('PASS 3968 original files, 393 profile inputs, 59 ASN.1 inputs per profile and original source/reference/output hashes')
