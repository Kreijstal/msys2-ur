"""Audit final Dataflow4.6 package against source archives and strict producer checks."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile

artifact,corefx,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(corefx.read_bytes())=='986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-dataflow46-bootstrap/';recipe=Path('mingw-w64-dotnet-dataflow46-bootstrap')
source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(corefx) as t:
    assert t.pax_headers['comment']==source['source_commit']=='9688ddbb62c04189cac4c4a06e31e93377dccd41'
    originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['original_file_sha256']}
assert {n:sha(b) for n,b in originals.items()}==source['original_file_sha256']
assert audit['production_CSharp_changes']==0
assert audit['original_compile_selections_and_feature_guards_preserved'] and audit['source_reference_DLL_bytes_verified'] and audit['warnings_as_errors']
assert audit['original_NS10_NS11_dependency_groups_preserved'] and audit['NS2_compatibility_DLL_bytes_identical_to_original_NS11']
assert set(source['profiles'])=={'netstandard1.0','netstandard1.1'}
assert all(v['production_CSharp_changes']==0 for v in source['profiles'].values())
assert all(c['exit_code']==0 for c in source['commands']+check['commands'])
for key in ['original_dependency_identities_equal','all_original_source_resource_values_verified','isolated_exact_old_implementations_executed','ordering_backpressure_batch_join_broadcast_write_once_cancellation_fault_checks_passed','fresh_NS2_PackageReference_consumer_passed','NS2_compatibility_DLL_bytes_identical_to_original_NS11']:assert check[key],key
assert check['original_public_API_entries_per_profile']==269
provenance=json.loads(files[doc+'inputs/published-provenance.json'])
assert not provenance['published_DLLs_executed_or_used_as_compiler_references']
for tfm in ['netstandard1.0','netstandard1.1']:
    baseline=files[doc+'inputs/original-dataflow-'+tfm+'.json'];assert sha(baseline)==provenance[tfm+'_baseline_sha256']
    assert len(json.loads(baseline)['System.Threading.Tasks.Dataflow.dll']['api'])==269
    original='src/System.Threading.Tasks.Dataflow/src/'+source['profiles'][tfm]['original_project']
    project=E.fromstring(originals[original]);assert project.findtext('.//{*}AssemblyVersion')=='4.6.0.0'
    assert audit['profiles'][tfm]['original_CSharp_inputs']==len(project.findall('.//{*}Compile'))+1
package=files['clang64/lib/dotnet/library-packs/system.threading.tasks.dataflow.4.6.0.nupkg']
assert sha(package)==audit['package_sha256']==check['exact_nupkg_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
    md=E.fromstring(z.read('System.Threading.Tasks.Dataflow.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='System.Threading.Tasks.Dataflow' and md.findtext('{*}version')=='4.6.0'
    assert md.find('{*}repository').get('commit')==source['source_commit']
    groups={g.get('targetFramework'):{d.get('id'):d.get('version') for d in g} for g in md.findall('{*}dependencies/{*}group')}
    assert groups==dict(provenance['original_dependency_groups'],**{'.NETStandard2.0':{'NETStandard.Library':'[2.0.3]'}})
    for tfm in ['netstandard1.0','netstandard1.1']:assert sha(z.read('lib/'+tfm+'/System.Threading.Tasks.Dataflow.dll'))==audit['profiles'][tfm]['DLL_sha256']
    for ext in ['dll','xml']:assert z.read('lib/netstandard2.0/System.Threading.Tasks.Dataflow.'+ext)==z.read('lib/netstandard1.1/System.Threading.Tasks.Dataflow.'+ext)
    for lic in ['LICENSE','THIRD-PARTY-NOTICES']:assert z.read(lic)==originals[lic]==files['clang64/share/licenses/dotnet-dataflow46-bootstrap/'+lic]
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
    verified=set()
    for m in t:
        name=m.name.partition('/')[2]
        if m.isfile() and name in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['README.md','check.py','inputs/Api.cs','inputs/Check.cs','inputs/Bridge.cs','inputs/original-dataflow-netstandard1.0.json','inputs/original-dataflow-netstandard1.1.json','inputs/source-contract-build-matrix.json','inputs/published-provenance.json']:assert files[doc+name]==(recipe/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(originals),profiles=audit['profiles'],unique_original_CSharp_inputs=audit['unique_original_CSharp_inputs'],production_CSharp_changes=0,original_public_API_entries_per_profile=269,original_dependency_identities_equal=True,source_resource_values_per_profile=19,isolated_original_NS10_NS11_and_NS2_consumer_passed=True,original_dependency_groups_preserved=True,NS2_compatibility_assets_byte_identical_to_NS11=True,nupkg_sha256=sha(package),original_source_csc44_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_historical_runtime_NuGet_closure_built=False,full_upstream_suite_run=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
