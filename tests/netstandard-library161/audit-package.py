"""Audit the genuine metadata-only package; prohibit implementation payloads."""
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
name = 'clang64/lib/dotnet/library-packs/netstandard.library.1.6.1.nupkg'
assert {p for p in files if p.endswith('.nupkg')} == {name}
assert not any(p.endswith(('.dll', '.exe')) for p in files)
assert files[name] == (producer / 'prepared/feed/NETStandard.Library.1.6.1.nupkg').read_bytes()
with zipfile.ZipFile(io.BytesIO(files[name])) as z: assert not any(p.endswith(('.dll', '.exe', '_._')) for p in z.namelist())
doc = 'clang64/share/doc/dotnet-netstandard-library161/'
check = json.loads(files[doc + 'producer-check-results.json'])
assert check['four_original_groups_and_128_edges_verified'] and check['six_original_framework_selection_checks_passed']
assert check['exact_fresh_cached_archive_verified']
for f in ['dotnet_library_license.txt', 'ThirdPartyNotices.txt', 'CoreFX-LICENSE', 'CoreFX-THIRD-PARTY-NOTICES']:
    assert 'clang64/share/licenses/dotnet-netstandard-library161/' + f in files
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    nupkg_sha256=hashlib.sha256(files[name]).hexdigest(), original_dependency_groups=4, original_dependency_edges=128,
    original_framework_selection_checks=6, implementation_or_marker_payloads=0, exact_checked_producer_bytes=True,
    full_legacy_framework_graph_complete=check['full_framework_implementation_graph_complete'], full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS original dependency-only source port: four groups/128 edges, exact archive bytes, original licenses; no implementation or marker payloads')
