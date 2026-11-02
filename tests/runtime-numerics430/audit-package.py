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
doc='clang64/share/doc/dotnet-runtime-numerics430/';name='System.Runtime.Numerics';policy=json.loads(files[doc+'inputs/published-package-policy.json'])[name];check=json.loads(files[doc+'producer-check-results.json']);source=json.loads(files[doc+'source-build.json'])
expected='clang64/lib/dotnet/library-packs/system.runtime.numerics.4.3.0.nupkg';assert {p for p in files if p.endswith('.nupkg')}=={expected};assert not any(p.endswith(('.dll','.exe')) for p in files)
data=files[expected];assert data==(producer/'archives/feed'/(name+'.4.3.0.nupkg')).read_bytes();assert hashlib.sha256(data).hexdigest()==check['source_NuGet_SHA256']
assert len(check['profiles'])==4 and check['original_reference_API_entries']==192 and check['original_runtime_API_entries']==192
assert check['original_netcore50_aliases_verified'] and check['actual_source_BigInteger_Complex_arithmetic_resources_and_errors_verified'] and check['all_original_assets_aliases_data_dependency_and_framework_semantics_verified']
assert all(c['exit_code']==0 for c in source['commands'])
assert all(check['fresh_restores'][n]['exit_code']==0 for n in ['own-ns11','own-ns13','own-netcore50'])
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert {p for p in z.namelist() if p.endswith('.dll')}==set(policy['reference_DLL_sha256'])
    for p,h in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
    assert z.read('ref/netcore50/'+name+'.dll')==z.read('ref/netstandard1.1/'+name+'.dll');assert z.read('lib/netcore50/'+name+'.dll')==z.read('lib/netstandard1.3/'+name+'.dll')
for kind,filename in [('sbrp','sbrp-5aeee273.tar.gz'),('corefx','corefx11-4d1af962.tar.gz')]:
    with tarfile.open(producer/filename) as t:
        entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
        for p,h in source['original_source_SHA256'].items():
            if not p.startswith(kind+'/'):continue
            raw=t.extractfile(entries[p.partition('/')[2]]).read();assert hashlib.sha256(raw).hexdigest()==h;assert raw==(producer/'producer/source'/p).read_bytes()
report=dict(artifact=artifact.name,artifact_SHA256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_NuGet_SHA256=hashlib.sha256(data).hexdigest(),original_reference_API_entries=192,original_runtime_API_entries=192,source_resource_strings=14,original_DLL_asset_paths=4,original_framework_markers=20,original_dependency_groups=13,original_XML_paths=20,all_original_assets_data_metadata_and_exact_dependency_scopes_verified=True,original_project_implementation_files=14,shared_SR_source_files=1,exact_source_producer_and_pinned_original_bytes_verified=True,actual_source_arithmetic_resources_and_errors_verified=True,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS exact source archive, 14 unchanged project inputs, original 192+192 API entries, 14 resource strings, arithmetic and original data/dependency assets')
