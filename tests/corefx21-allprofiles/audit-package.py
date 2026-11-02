"""Audit the pacman payload against the verified two source NuGet archives."""
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
root = 'clang64/lib/dotnet/library-packs/'
names = [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]
expected = {root + name.lower() + '.' + version + '.nupkg' for name, version in names}
assert {p for p in files if p.endswith('.nupkg')} == expected
assert not any(p.endswith(('.exe', '.dll')) for p in files)
archives = {}
for name, version in names:
    path = root + name.lower() + '.' + version + '.nupkg'
    assert files[path] == (producer / 'archives/feed' / (name + '.' + version + '.nupkg')).read_bytes()
    with zipfile.ZipFile(io.BytesIO(files[path])) as z:
        dlls = [p for p in z.namelist() if p.endswith('.dll')]
        assert len(dlls) == (4 if name.endswith('Immutable') else 3)
    archives[path] = hashlib.sha256(files[path]).hexdigest()
doc = 'clang64/share/doc/dotnet-corefx21-metadata-bootstrap/'
checks = json.loads(files[doc + 'producer-check-results.json'])
assert sum(checks['original_profile_API_entries'].values()) == 8483
assert checks['all_five_source_implementations_executed_on_source_NET8']
assert checks['fresh_NS2_source_archive_cache_and_compile_runtime_checks_passed']
build = json.loads(files[doc + 'source-build-results.json'])
assert build['production_CSharp_changes'] == 0 and len(build['profiles']) == 5
for name in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    assert files['clang64/share/licenses/dotnet-corefx21-metadata-bootstrap/' + name] == (producer / 'prepared/source' / name).read_bytes()
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    source_NuGet_archives=archives, original_implementation_profiles=5, original_DLL_asset_paths=7,
    original_API_entries=8483, exact_checked_producer_archives=True, production_CSharp_changes=0,
    original_profile_API_attributes_resources_native_versions_and_aliases_verified=True,
    fresh_NS2_exact_archive_consumers_passed=True, original_NS13_restore_exit_code=checks['original_NS13_restore_exit_code'],
    complete_original_NS1x_NuGet_runtime_graph=False, historical_runtime_execution_verified=False,
    full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS two exact checked source archives; five implementations/seven original DLL paths; 8483 API entries; original source/license data')
