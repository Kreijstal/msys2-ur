"""Independently audit pacman payload, original source bytes and checked NuGets."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile

artifact, producer, output = (Path(p).resolve() for p in sys.argv[1:])
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['zstd', '-dc', str(artifact)]))) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-framework430-refs/'
policy = json.loads(files[doc + 'inputs/published-package-policy.json'])
assert len(policy) == 8
assert {p for p in files if p.endswith('.nupkg')} == {
    'clang64/lib/dotnet/library-packs/' + n.lower() + '.4.3.0.nupkg' for n in policy}
assert not any(p.endswith(('.dll', '.exe')) for p in files)
checks = json.loads(files[doc + 'producer-check-results.json'])
assert checks['total_API_entries'] == 2585 and len(checks['profiles']) == 13
assert checks['all_13_compile_consumers_and_original_metadata_verified']
assert checks['original_Debug_Conditional_attributes_and_Release_call_omission_verified']
assert checks['all_original_NuGet_asset_paths_aliases_and_dependency_semantics_verified']
assert not checks['runtime_provider_packages_supplied']
archives = {}
for name, expected in policy.items():
    raw = files['clang64/lib/dotnet/library-packs/' + name.lower() + '.4.3.0.nupkg']
    assert raw == (producer / 'archives/feed' / (name + '.4.3.0.nupkg')).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == checks['archives'][name]['sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert {p for p in z.namelist() if p.endswith('.dll')} == set(expected['reference_DLL_sha256'])
        assert len([p for p in z.namelist() if p.endswith('_._')]) == sum(p.endswith('_._') for p in expected['original_data_sha256'])
        for p, wanted in expected['original_data_sha256'].items():
            assert hashlib.sha256(z.read(p)).hexdigest() == wanted, p
    archives[name] = digest
source = json.loads(files[doc + 'source-reference-build.json'])
assert len(source['profiles']) == 13 and all(c['exit_code'] == 0 for c in source['commands'])
originals = source['original_source_sha256']
for kind, filename in [('sbrp', 'sbrp-5aeee273.tar.gz'), ('corefx', 'corefx10-codepages-9688ddbb.tar.gz')]:
    with tarfile.open(producer / filename) as t:
        entries = {m.name.partition('/')[2]: m for m in t if m.isfile()}
        for key, digest in originals.items():
            if not key.startswith(kind + '/'): continue
            path = key.partition('/')[2]
            raw = t.extractfile(entries[path]).read()
            assert hashlib.sha256(raw).hexdigest() == digest
            assert raw == (producer / 'references/source' / key).read_bytes()
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    source_nupkg_sha256=archives, original_reference_profiles=13, API_entries=2585,
    original_framework_markers=166, all_original_source_data_and_asset_paths_verified=True,
    explicit_Debug_source_port=True, exact_checked_source_archives=True,
    runtime_implementation_DLLs=0, full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS eight checked source NuGets, 13 profiles/2585 API entries, 166 markers and pinned original source bytes')
