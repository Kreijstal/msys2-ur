"""Audit exact original source inputs, the sole backport, profiles and output hashes."""
from pathlib import Path
import difflib, hashlib, json, sys, tarfile

archive, win, portable, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
w = json.loads((win / 'results.json').read_text())
p = json.loads((portable / 'results.json').read_text())
source = Path(w['source_root'])
with tarfile.open(archive) as t:
    manifest = json.load(t.extractfile('source-inputs.json'))
    assert len(manifest['files']) == 1331
    for rel, h in manifest['files'].items():
        assert hashlib.sha256(t.extractfile('corefx/' + rel).read()).hexdigest() == sha(source / rel) == h, rel
assert w['original_configuration'] == 'netstandard-Windows_NT' and p['original_configuration'] == 'netstandard'
assert w['original_production_source_changes'] == 1 and p['original_production_source_changes'] == 0
assert len(w['original_source_sha256']) == 11
for rel, h in w['original_source_sha256'].items():
    assert sha(source / rel) == h == manifest['files'][rel], rel
overlay = w['production_overlay']
original = source / 'src/System.Security.Cryptography.ProtectedData/src/System/Security/Cryptography/ProtectedData.cs'
patched = Path(overlay['path'])
assert sha(original) == overlay['original_sha256'] and sha(patched) == overlay['sha256']
rel = original.relative_to(source).as_posix()
diff = ''.join(difflib.unified_diff(original.read_text().splitlines(True), patched.read_text().splitlines(True), fromfile='a/' + rel, tofile='b/' + rel))
here = Path(__file__).resolve().parent
assert diff == (here / '0001-handle-empty-input-in-native-DPAPI.patch').read_text()
assert sha(here / '0001-handle-empty-input-in-native-DPAPI.patch') == overlay['patch_sha256']
assets = {}
for label, root, record in [('windows', win, w), ('portable', portable, p)]:
    for ext, h in record['output_sha256'].items():
        f = root / 'bin' / ('System.Security.Cryptography.ProtectedData.' + ext)
        assert sha(f) == h
        assets[label + '/' + f.name] = h
    for f, h in record['generated_source_sha256'].items():
        assert sha(Path(f)) == h
for f, h in w['reference_sha256'].items():
    assert sha(Path(f)) == h
assert p['original_contract_source_sha256'] == sha(source / 'src/System.Security.Cryptography.ProtectedData/ref/System.Security.Cryptography.ProtectedData.cs')
report = dict(original_source_files_verified=1331, original_windows_compile_inputs=11,
    original_configuration_profiles_preserved=['netstandard-Windows_NT', 'netstandard'],
    original_assembly_version='4.0.2.0', original_file_version='4.6.25519.03',
    Windows_empty_input_backport_files=1, original_source_and_overlay_hashes_verified=True,
    producer_asset_sha256=assets, original_2017_toolchain_reproduced=False,
    original_NETFramework_and_harvested_profiles_built=False, full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print('PASS 1331 original files, 11 Windows compile inputs, one explicit backport and both profiles/output hashes')
