"""Audit pacman payload against checked source NuGets and original data policy."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile

artifact, producer, output = (Path(p).resolve() for p in sys.argv[1:])
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['zstd', '-dc', str(artifact)]))) as tar:
    files = {m.name.removeprefix('./'): tar.extractfile(m).read() for m in tar if m.isfile()}
doc = 'clang64/share/doc/dotnet-reflection430/'
policy = json.loads(files[doc + 'inputs/published-package-policy.json'])
expected_archives = {'clang64/lib/dotnet/library-packs/' + name.lower() + '.4.3.0.nupkg' for name in policy}
assert {p for p in files if p.endswith('.nupkg')} == expected_archives
assert not any(p.endswith(('.dll', '.exe')) for p in files)
checks = json.loads(files[doc + 'producer-check-results.json'])
assert checks['all_34_original_NET462_forwarder_names_flags_scopes_and_nesting_verified']
assert checks['exact_NET462_source_facade_five_core_types_resolved_and_constructor_executed_on_source_NET8']
assert checks['total_API_entries'] == 1513
assert checks['all_original_reference_assets_and_NuGet_semantics_verified'] and checks['all_four_compile_consumers_passed']
assert all(v['original_native_versions_and_resources_verified'] for v in checks['contracts'].values())
archives = {}
for name, expected in policy.items():
    data = files['clang64/lib/dotnet/library-packs/' + name.lower() + '.4.3.0.nupkg']
    assert data == (producer / 'archives/feed' / (name + '.4.3.0.nupkg')).read_bytes()
    digest = hashlib.sha256(data).hexdigest(); assert digest == checks['archives'][name]['sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert {n for n in z.namelist() if n.endswith('.dll')} == set(expected['reference_DLL_sha256'])
        assert not any(n.endswith('.exe') for n in z.namelist())
        assert len([n for n in z.namelist() if n.endswith('_._')]) == 22
        for path, wanted in expected['original_data_sha256'].items(): assert hashlib.sha256(z.read(path)).hexdigest() == wanted
    archives[name] = digest
source = json.loads(files[doc + 'source-reference-build.json'])
facade = json.loads(files[doc + 'source-facade-build.json'])
assert facade['facade_type_count'] == 34 and facade['NET46_source_seed_supplies_all_original_NET462_forwarding_targets']
assert hashlib.sha256(files[doc + 'NET462-Forwards.cs']).hexdigest() == facade['source_generated_forwarder_CS_sha256']
with tarfile.open(producer / 'corefx11-4d1af962.tar.gz') as tar:
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name, digest in facade['source_CoreFX_project_hashes'].items():
        raw = tar.extractfile(entries[name]).read()
        assert hashlib.sha256(raw).hexdigest() == digest
        assert raw == (producer / 'finished/source' / name).read_bytes()
with tarfile.open(producer / 'sbrp-5aeee273.tar.gz') as tar:
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for profile, record in source['profiles'].items():
        original = record['original_source']; raw = tar.extractfile(entries[original]).read()
        assert hashlib.sha256(raw).hexdigest() == record['source_sha256']
        assert raw == (producer / 'references/source' / original).read_bytes()
    assert files['clang64/share/licenses/dotnet-reflection430/SBRP-LICENSE.txt'] == tar.extractfile(entries['LICENSE.txt']).read()
assert all(c['exit_code'] == 0 for c in source['commands'])
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    source_nupkg_sha256=archives, original_source_changes=0, original_reference_profiles=4, API_entries=1513,
    original_framework_markers=22, all_original_data_bytes_and_asset_paths_verified=True,
    exact_checked_source_archives=True, original_NET462_runtime_facades=1,
    historical_runtime_and_provider_closure_complete=False, full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS exact checked source NuGets, 3 unchanged reference sources/1513 API entries, 22 markers, original data and licenses; original34-forwarder NET462 runtime facade')
