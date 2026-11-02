"""Independently audit the producer archive and pinned original carrier source."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile

artifact,producer,output=(Path(p).resolve() for p in sys.argv[1:])
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['zstd','-dc',str(artifact)]))) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-private-uri430/';name='clang64/lib/dotnet/library-packs/system.private.uri.4.3.0.nupkg'
assert {f for f in files if f.endswith('.nupkg')}=={name}
assert not any(f.endswith(('.dll','.exe')) for f in files)
data=files[name];assert data==(producer/'producer/feed/System.Private.Uri.4.3.0.nupkg').read_bytes()
policy=json.loads(files[doc+'inputs/policy.json']);source=json.loads(files[doc+'source-build.json']);check=json.loads(files[doc+'producer-check-results.json'])
assert check['source_NuGet_SHA256']==hashlib.sha256(data).hexdigest()
assert all(c['exit_code']==0 for c in check['checks'])
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert not any(f.endswith('.dll') for f in z.namelist())
    for f,digest in policy['original_data_SHA256'].items():assert hashlib.sha256(z.read(f)).hexdigest()==digest
with tarfile.open(producer/'corefx11-4d1af962.tar.gz') as t:
    entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
    for name,digest in source['original_source_SHA256'].items():
        raw=t.extractfile(entries[name]).read();assert hashlib.sha256(raw).hexdigest()==digest
        assert raw==(producer/'producer/source'/name).read_bytes()
output.write_text(json.dumps(dict(artifact=artifact.name,artifact_SHA256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_NuGet_SHA256=hashlib.sha256(data).hexdigest(),original_DLL_count=0,all_original_data_and_pinned_source_verified=True,fresh_restore_checks=2,runtime_implementation_not_claimed=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS independent source/data/DLL-free carrier audit and original source archive hashes')
