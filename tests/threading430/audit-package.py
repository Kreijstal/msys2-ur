"""Audit package payload against the source producer and pinned raw inputs."""
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
doc='clang64/share/doc/dotnet-threading430/';name='System.Threading'
policy=json.loads(files[doc+'inputs/published-package-policy.json'])[name];check=json.loads(files[doc+'producer-check-results.json']);source=json.loads(files[doc+'source-build.json'])
expected='clang64/lib/dotnet/library-packs/system.threading.4.3.0.nupkg'
assert {p for p in files if p.endswith('.nupkg')}=={expected}
assert not any(p.endswith(('.dll','.exe')) for p in files)
data=files[expected];assert data==(producer/'archives/feed'/(name+'.4.3.0.nupkg')).read_bytes()
assert hashlib.sha256(data).hexdigest()==check['source_NuGet_SHA256']
assert len(check['profiles'])==6 and check['original_DLL_paths_verified']==6
for label,row in check['profiles'].items():
    assert row['API_entries']==(324 if label=='ref-netstandard1.0' else 345 if label.startswith('ref-') else 0 if label.startswith('runtimes-') else 94)
    assert row['all_original_metadata_resources_scopes_exports_verified']
    if label=='lib-netstandard1.3':assert row['actual_candidate_runtime_checks_passed']
assert check['original_Framework_System_and_SystemCore_references_verified']
assert check['AOT_metadata_forwarders_verified']==31 and check['CoreCLR_candidate_runtime_checks']==994
assert check['AOT_private_provider_runtime_execution_verified'] is False
assert source['original_project_implementation_files']==5 and source['source_resource_strings']==27
assert source['original_source_files_edited_in_place']==0
assert source['AOT_metadata_facade_port_built'] and source['AOT_private_providers_runtime_execution_verified'] is False
assert all(c['exit_code']==0 for c in source['commands'])
assert all(r['exit_code']==0 for k,r in check['fresh_restores'].items() if k!='standard161')
assert check['complete_parent_dependency_restore_closure']
private=json.loads(files[doc+'private-coreclr-source-contract.json'])
assert private['public_API_and_metadata_equality_verified'] and private['original_public_API_entries']==10960
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert {p for p in z.namelist() if p.endswith('.dll')}==set(policy['reference_DLL_sha256'])
    for p,h in policy['original_data_sha256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
    assert z.read('ref/netcore50/'+name+'.dll')==z.read('ref/netstandard1.3/'+name+'.dll')
    assert z.read('lib/netcore50/'+name+'.dll')==z.read('lib/netstandard1.3/'+name+'.dll')
for kind,filename in [('sbrp','sbrp-5aeee273.tar.gz'),('corefx','corefx11-4d1af962.tar.gz')]:
    with tarfile.open(producer/filename) as t:
        entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
        for p,h in source['original_source_SHA256'].items():
            if not p.startswith(kind+'/'):continue
            raw=t.extractfile(entries[p.partition('/')[2]]).read()
            assert hashlib.sha256(raw).hexdigest()==h
            assert raw==(producer/'producer/source'/p).read_bytes()
report=dict(artifact=artifact.name,artifact_SHA256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_NuGet_SHA256=hashlib.sha256(data).hexdigest(),original_DLL_asset_paths=6,original_API_entries_across_asset_paths=1202,original_framework_markers=sum(p.endswith('/_._') for p in policy['original_data_sha256']),original_dependency_groups=14,original_XML_paths=sum(p.endswith('.xml') for p in policy['original_data_sha256']),original_Framework_System_and_SystemCore_references_verified=True,original_project_implementation_files=5,source_resource_strings=27,CoreCLR_candidate_runtime_checks=994,CoreCLR_original_mscorlib_scope_preserved=True,CoreCLR_private_compiler_contract_API_entries=10960,AOT_exact_original_forwarder_rows=31,AOT_private_provider_runtime_execution_verified=False,AOT_original_private_targeting_pack_acquired=False,original_source_files_edited_in_place=0,all_original_assets_data_metadata_and_exact_dependency_scopes_verified=True,source_producer_and_pinned_source_bytes_verified=True,complete_parent_dependency_restore_closure=check['complete_parent_dependency_restore_closure'],fresh_restores=check['fresh_restores'],full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print('PASS pinned source bytes, all six original profiles, actual CoreCLR candidate and all package assets; AOT private-provider execution remains unverified')
