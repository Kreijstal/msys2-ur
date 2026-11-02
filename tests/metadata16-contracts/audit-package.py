"""Verify the reference-only package payload against its checked producer."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile

artifact, producer, output = (Path(p).resolve() for p in sys.argv[1:])
raw = subprocess.check_output(['zstd', '-dc', str(artifact)])
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
    files = {m.name.removeprefix('./'): tar.extractfile(m).read() for m in tar if m.isfile()}
root = 'clang64/lib/dotnet/reference-packs/metadata16-ns11-contracts-bootstrap/ref/'
names = ['System.IO.Compression', 'System.Reflection.Extensions', 'System.Text.Encoding.Extensions', 'System.Runtime.InteropServices']
expected = {root + name + '.dll' for name in names}
assert {p for p in files if p.endswith('.dll')} == expected
assert not any(p.endswith(('.nupkg', '.exe')) for p in files)
payload = {}
for name in names:
    path = root + name + '.dll'
    assert files[path] == (producer / 'ref' / (name + '.dll')).read_bytes()
    payload[path] = hashlib.sha256(files[path]).hexdigest()
doc = 'clang64/share/doc/dotnet-metadata16-contracts-bootstrap/'
result = json.loads(files[doc + 'producer-check-results.json'])
assert sum(result['original_API_entries'].values()) == 1172
interop = json.loads(files[doc + 'producer-interop-check-results.json'])
assert interop['original_COM_layout_field_offsets_and_Conditional_attributes_verified']
for name in ['SBRP-LICENSE.txt', 'CoreFX-LICENSE.txt', 'THIRD-PARTY-NOTICES']:
    assert 'clang64/share/licenses/dotnet-metadata16-contracts-bootstrap/' + name in files
report = dict(artifact=artifact.name, artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    source_reference_DLLs=4, original_API_entries=1172, exact_producer_payload_bytes=True,
    original_Interop_layout_and_Conditional_checks_passed=True, runtime_implementation_or_NuGet_payloads=0,
    payload_sha256=payload, full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS four source reference DLL payloads; 1172 original API entries; licenses and producer evidence; no runtime/NuGet payloads')
