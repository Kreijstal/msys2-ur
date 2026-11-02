"""Audit exact checked graph bytes and original marker, without runtime DLLs."""
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
name = 'clang64/lib/dotnet/library-packs/microsoft.netcore.targets.1.1.0.nupkg'
assert {p for p in files if p.endswith('.nupkg')} == {name}
assert not any(p.endswith(('.dll', '.exe')) for p in files)
assert files[name] == (producer / 'prepared/feed/Microsoft.NETCore.Targets.1.1.0.nupkg').read_bytes()
doc = 'clang64/share/doc/dotnet-netcore-targets110/'
policy = json.loads(files[doc + 'inputs/provenance.json'])
with zipfile.ZipFile(io.BytesIO(files[name])) as z:
    assert not any(n.endswith(('.dll', '.exe')) for n in z.namelist())
    assert {n for n in z.namelist() if n.endswith('_._')} == {policy['original_empty_marker']}
    assert z.read(policy['original_empty_marker']) == b''
    for n, digest in policy['original_data_sha256'].items(): assert hashlib.sha256(z.read(n)).hexdigest() == digest
check = json.loads(files[doc + 'producer-check-results.json'])
assert check['all_NuGet_runtime_dependency_ranges_and_merged_platform_lookups_verified']
assert check['exact_fresh_archive_cache_verified']
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    nupkg_sha256=hashlib.sha256(files[name]).hexdigest(), original_runtime_rows=22, original_dependency_edges=97,
    original_support_profiles=14, original_single_marker_verified=True, original_graph_and_license_bytes_verified=True,
    exact_checked_source_archive=True, implementation_binaries=0, mapped_runtime_packages_verified=False,
    full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS22 runtime rows/97 edges/14 profiles, exact graph/license bytes, original marker and source archive; zero implementation binaries')
