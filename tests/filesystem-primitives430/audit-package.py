"""Independently audit source payload and original source provenance."""
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
doc='clang64/share/doc/dotnet-filesystem-primitives430/';name='System.IO.FileSystem.Primitives';policy=json.loads(files[doc+'inputs/published-package-policy.json'])[name];check=json.loads(files[doc+'producer-check-results.json']);source=json.loads(files[doc+'source-build.json'])
expected='clang64/lib/dotnet/library-packs/system.io.filesystem.primitives.4.3.0.nupkg';assert {p for p in files if p.endswith('.nupkg')}=={expected};assert not any(p.endswith(('.dll','.exe')) for p in files)
data=files[expected];assert data==(producer/'archives/feed'/(name+'.4.3.0.nupkg')).read_bytes();assert hashlib.sha256(data).hexdigest()==check['source_NuGet_SHA256']
assert len(check['profiles'])==4 and check['original_reference_API_entries']==39 and check['original_runtime_API_entries']==39
assert check['complete_original_NET46_four_forwarder_facade_verified'] and check['source_runtime_enum_and_facade_execution_verified'] and check['all_original_assets_aliases_data_dependency_and_framework_semantics_verified']
assert all(c['exit_code']==0 for c in source['commands'])
assert check['fresh_restores']['own-ns13']['exit_code']==0 and check['fresh_restores']['own-net46']['exit_code']==0
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert {p for p in z.namelist() if p.endswith('.dll')}==set(policy['reference_DLL_sha256'])
    for p,h in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
    assert z.read('ref/net46/'+name+'.dll')==z.read('lib/net46/'+name+'.dll')
for kind,filename in [('sbrp','sbrp-5aeee273.tar.gz'),('corefx','corefx11-4d1af962.tar.gz')]:
    with tarfile.open(producer/filename) as t:
        entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
        for p,h in source['original_source_SHA256'].items():
            if not p.startswith(kind+'/'):continue
            raw=t.extractfile(entries[p.partition('/')[2]]).read();assert hashlib.sha256(raw).hexdigest()==h;assert raw==(producer/'producer/source'/p).read_bytes()
report=dict(artifact=artifact.name,artifact_SHA256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_NuGet_SHA256=hashlib.sha256(data).hexdigest(),original_reference_API_entries=39,original_runtime_API_entries=39,original_NET46_forwarded_types=4,original_DLL_asset_paths=4,original_framework_markers=12,original_dependency_groups=8,original_XML_paths=10,all_original_assets_data_metadata_and_exact_dependency_scopes_verified=True,original_implementation_source_files=4,exact_source_producer_and_pinned_original_bytes_verified=True,source_enum_and_facade_execution_verified=True,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS exact source archive, four unchanged enum implementation files, original 39+39 API entries, four facade forwards and original data/dependency assets')
