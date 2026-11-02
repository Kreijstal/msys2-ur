"""Audit final package payload, original-source metadata and all NuGet asset bytes."""
from pathlib import Path
import difflib, hashlib, io, json, sys, tarfile, xml.etree.ElementTree as E, zipfile

artifact, snapshot, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes()) == 'c69ee661412027223f5236819e653bf2d0a7d593a7e487f78d34616ec52bbf99'
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-protecteddata44/'
binary = 'clang64/lib/dotnet/library-packs/protecteddata-4.4.0-netstandard2-bootstrap/'
manifest = json.loads(files[doc + 'payload-sha256.json'])
for rel, h in manifest.items():
    assert sha(files['clang64/' + rel]) == h, rel
assert {n for n in files if n.startswith('clang64/')} == {'clang64/' + n for n in manifest} | {doc + 'payload-sha256.json'}
windows = json.loads(files[doc + 'windows-build-results.json'])
portable = json.loads(files[doc + 'portable-build-results.json'])
assert windows['original_production_source_changes'] == 1 and portable['original_production_source_changes'] == 0
assert windows['framework_reference_profile'] == portable['framework_reference_profile'] == 'netstandard2.0'
regression = json.loads(files[doc + 'empty-input-regression-results.json'])
assert regression['original_source_empty_input_failure_reproduced_after_native_success'] and regression['expected_negative_case_exit_code'] != 0
with tarfile.open(snapshot) as source:
    inputs = json.load(source.extractfile('source-inputs.json'))
    assert len(inputs['files']) == 1331
    for rel, h in windows['original_source_sha256'].items():
        assert sha(source.extractfile('corefx/' + rel).read()) == h == inputs['files'][rel]
    original = source.extractfile('corefx/src/System.Security.Cryptography.ProtectedData/src/System/Security/Cryptography/ProtectedData.cs').read()
    assert sha(original) == windows['production_overlay']['original_sha256']
assert sha(files[doc + '0001-handle-empty-input-in-native-DPAPI.patch']) == windows['production_overlay']['patch_sha256']
assert len(windows['original_source_sha256']) == 11
for label, record in [('windows', windows), ('portable', portable)]:
    api = json.loads(files[doc + label + '-api-results.json'])
    assert api['exit_code'] == 0 and api['comparison']['expected_entries'] == 7
    assert api['comparison']['total_differences'] == 0 and not api['comparison']['nullable_annotation_differences']
    assert api['implementation_sha256'] == record['output_sha256']['dll']
    for ext, h in record['output_sha256'].items():
        assert sha(files[binary + label + '/System.Security.Cryptography.ProtectedData.' + ext]) == h
archive = json.loads(files[doc + 'archive.json'])
data = files['clang64/' + archive['archive']]
assert sha(data) == archive['sha256']
name = 'System.Security.Cryptography.ProtectedData'
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert set(z.namelist()) == set(archive['members'])
    for n, h in archive['members'].items():
        assert sha(z.read(n)) == h
    meta = E.fromstring(z.read(name + '.nuspec')).find('metadata')
    assert meta.findtext('id') == name and meta.findtext('version') == '4.4.0'
    assert meta.find('repository').get('commit') == '8321c729934c0f8be754953439b88e6e1c120c24'
    assert meta.find('dependencies/group').get('targetFramework') == 'netstandard2.0'
    assert not list(meta.find('dependencies/group'))
    for label, record, path in [('windows', windows, 'runtimes/win/lib/netstandard2.0/'), ('portable', portable, 'lib/netstandard2.0/')]:
        for ext, h in record['output_sha256'].items():
            assert sha(z.read(path + name + '.' + ext)) == h
    h = json.loads(files[doc + 'windows-api-results.json'])['reference_contract_sha256']
    assert sha(z.read('ref/netstandard2.0/' + name + '.dll')) == sha(files[binary + 'ref/' + name + '.dll']) == h
assert len([n for n in files if n.startswith(binary)]) == 5
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()), payload_files=len(manifest),
    original_source_snapshot_files=1331, original_Windows_compile_inputs=11, explicit_backport_files=1,
    source_reference_Windows_and_portable_assets=5, checked_CLR_and_nullable_entries=14,
    strict_CLR_and_nullable_gate_passed=True, exact_NuGet440_NS2_asset_layout_verified=True,
    original_2017_toolchain_reproduced=False, original_NETFramework_and_harvested_profiles_built=False,
    full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
