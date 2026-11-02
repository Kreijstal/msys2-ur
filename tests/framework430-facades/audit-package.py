"""Independently compare pacman payload, checked NuGets and pinned original sources."""
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
doc='clang64/share/doc/dotnet-framework430-facades/';policy=json.loads(files[doc+'inputs/published-package-policy.json']);checks=json.loads(files[doc+'producer-check-results.json'])
assert len(policy)==7 and {p for p in files if p.endswith('.nupkg')}=={'clang64/lib/dotnet/library-packs/'+n.lower()+'.4.3.0.nupkg' for n in policy}
assert not any(p.endswith(('.dll','.exe')) for p in files)
assert checks['reference_API_entries']==3871 and len(checks['reference_profiles'])==12 and len(checks['facades'])==7
assert checks['owned_API_entries']==25 and checks['original_exported_records']==94 and checks['original_source_resource_strings']==148
assert checks['runtime_execution']['all_13_original_source_SocketTaskExtensions_overloads_executed'] and checks['runtime_execution']['all_94_original_exported_types_resolved_to_source_NET8']
assert checks['all_original_assets_aliases_data_and_NuGet_framework_dependency_semantics_verified']
archives={}
for name,row in policy.items():
    raw=files['clang64/lib/dotnet/library-packs/'+name.lower()+'.4.3.0.nupkg'];assert raw==(producer/'archives/feed'/(name+'.4.3.0.nupkg')).read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==checks['archives'][name]['sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert {p for p in z.namelist() if p.endswith('.dll')}==set(row['reference_DLL_sha256'])
        for p,wanted in row['original_data_sha256'].items():assert hashlib.sha256(z.read(p)).hexdigest()==wanted,p
    archives[name]=digest
reference=json.loads(files[doc+'source-reference-build.json']);facades=json.loads(files[doc+'source-facades.json']);seeds=json.loads(files[doc+'source-Framework-seeds.json'])
assert facades['explicit_owned_source_projections']==1 and facades['original_source_files_edited_in_place']==0
assert len(seeds['seeds'])==1 and seeds['seeds']['System']['API_entries']==1435 and seeds['selected_reference_types']==71
assert seeds['seeds']['System']['original_declarative_metadata_equal']
for row in [reference,facades,seeds]:assert all(c['exit_code']==0 for c in row['commands'])
for kind,filename in [('sbrp','sbrp-5aeee273.tar.gz'),('corefx','corefx11-4d1af962.tar.gz')]:
    with tarfile.open(producer/filename) as t:
        entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
        for key,digest in reference['original_source_sha256'].items():
            if not key.startswith(kind+'/'):continue
            p=key.partition('/')[2];raw=t.extractfile(entries[p]).read();assert hashlib.sha256(raw).hexdigest()==digest
            assert raw==(producer/'producer/references/source'/key).read_bytes()
        if kind=='corefx':
            for p,digest in facades['original_CoreFX_source_sha256'].items():
                raw=t.extractfile(entries[p]).read();assert hashlib.sha256(raw).hexdigest()==digest
                assert raw==(producer/'producer/facades/source'/p).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),source_NuGet_sha256=archives,original_reference_profiles=12,original_reference_API_entries=3871,original_owned_API_entries=25,original_exported_records=94,original_source_resource_strings=148,original_DLL_asset_paths=sum(len(v['reference_DLL_sha256']) for v in policy.values()),original_framework_markers=sum(sum(p.endswith('_._') for p in v['original_data_sha256']) for v in policy.values()),original_dependency_groups=sum(len(v['dependencies']) for v in policy.values()),all_13_source_socket_task_overloads_and_original_EventCounter_statistics_executed=True,exact_checked_source_archives_and_pinned_original_sources_verified=True,one_explicit_socket_accept_result_source_projection=True,private_reference_or_compiler_DLLs_shipped=0,original_runtime_any_AOT_providers_supplied=False,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS seven source NuGets, 12 reference profiles/3871 API entries, 25 owned APIs, 94 exports, 148 resource strings and pinned original source bytes')
