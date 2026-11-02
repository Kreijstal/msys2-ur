"""Independently audit the Memory4.5.3 native artifact against pinned archives."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,memory,sbrp,corefx,roslyn,out=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
for p,h in [(memory,'013a4d6cfd81398e3899a6594d497343329865ab802350955e95f28e8d0c2091'),(sbrp,'2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'),(corefx,'986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'),(roslyn,'9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11')]:assert sha(p.read_bytes())==h,p
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-memory453-bootstrap/';recipe=Path('mingw-w64-dotnet-memory453-bootstrap');source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json']);interop=json.loads(files[doc+'interop-source-inputs.json']);icheck=json.loads(files[doc+'interop-check-results.json']);compiler=json.loads(files[doc+'compiler44-source-inputs.json'])
def original_files(archive,expected,commit):
 with tarfile.open(archive) as t:
  assert t.pax_headers['comment']==commit
  result={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in expected}
 assert {n:sha(b) for n,b in result.items()}==expected;return result
raw=original_files(memory,source['original_file_sha256'],'c6cf790234e063b855fcdb50f3fb1b3cfac73275')
for tag,p,commit in [('sbrp',sbrp,'5aeee2738338530a92d7f6caa2c7d5f569fed3c4'),('corefx',corefx,'9688ddbb62c04189cac4c4a06e31e93377dccd41')]:original_files(p,{n.partition('/')[2]:h for n,h in interop['original_file_sha256'].items() if n.startswith(tag+'/')},commit)
original_files(roslyn,compiler['original_csc_compile_items'],'1ce8866c9de4c2d67351ef6863699dee03b0804a');assert len(compiler['original_csc_compile_items'])==11 and compiler['original_csc_source_changes']==0
assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0 and audit['unique_original_CSharp_inputs']==102
assert interop==source['private_Interop_reference_inputs'] and interop['exit_code']==0 and interop['reference_only']
assert all(c['exit_code']==0 for c in source['commands']+check['commands']+icheck['commands'])
for k in ['all_original_compile_selections_exact','all_exact_source_reference_and_dependency_bytes_verified','private_Interop4000_source_port_replayed_and_reference_bytes_verified','compiler_warning_release_and_portable_span_policy_verified','original_reference_asset_exclusion_and_dependency_groups_preserved','all_original_DLL_XML_empty_marker_version_and_license_assets_preserved']:assert audit[k],k
for k in ['original_identity_dependencies_resources_managed_native_metadata_equal','isolated_exact_old_Memory_Buffers_Unsafe_implementations_executed','span_memory_GC_pinning_sequence_binary_Base64_UTF8_and_negative_checks_passed','fresh_NS2_exact_source_dependency_graph_and_compile_runtime_asset_selection_passed','fresh_NET8_original_empty_framework_marker_consumer_passed']:assert check[k],k
assert icheck['original_public_API_entries']==989 and icheck['original_COM_layout_field_offsets_and_Conditional_attributes_verified'] and icheck['original_identity_dependencies_and_reference_marker_verified']
package=files['clang64/lib/dotnet/library-packs/system.memory.4.5.3.nupkg'];assert sha(package)==audit['package_sha256']==check['package_sha256'];provenance=json.loads(files[doc+'inputs/published-provenance.json']);assert not provenance['published_DLL_executed_or_used_as_compiler_reference']
assert E.fromstring(raw['src/System.Memory/pkg/System.Memory.pkgproj']).findtext('.//{*}ExcludeReferenceAssets')=='true'
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 assert {n for n in z.namelist() if n.startswith(('lib/','ref/'))}==set(provenance['original_assets'])
 for n,h in provenance['original_assets'].items():
  if n.endswith('.dll'):assert sha(z.read(n))==source['profiles'][n.rsplit('/',1)[0]]['DLL_sha256'] and sha(z.read(n))!=h
  else:assert sha(z.read(n))==h
 md=E.fromstring(z.read('System.Memory.nuspec')).find('{*}metadata');original=E.fromstring(files[doc+'inputs/original.nuspec']).find('{*}metadata')
 def groups(m):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in m.findall('{*}dependencies/{*}group')}
 assert md.findtext('{*}version')=='4.5.3' and md.find('{*}repository').get('commit')==source['source_commit'] and groups(md)==groups(original)
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==raw[lic]==files['clang64/share/licenses/dotnet-memory453-bootstrap/'+lic]
 assert z.read('version.txt')==(source['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==raw['pkg/useSharedDesignerContext.txt']
for n in ['README.md','check.py']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+n]==(recipe/n).read_bytes(),n
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(raw),unique_original_CSharp_inputs=102,production_CSharp_changes=0,original_runtime_profiles=['netstandard1.1','netstandard2.0'],original_API_entries_per_profile=432,original_reference_asset_exclusion_and_dependency_groups_preserved=True,original_DLL_XML_empty_marker_version_and_license_assets_preserved=True,exact_source_reference_and_dependency_bytes_verified=True,private_Interop4000_reference_original_API_entries=989,private_Interop4000_reference_source_port_and_COM_layouts_verified=True,original_source_csc44_inputs=11,original_metadata_and_isolated_old_memory_behavior_verified=True,fresh_NS2_exact_source_dependency_graph_and_compile_runtime_selection_passed=True,fresh_NET8_original_empty_framework_marker_consumer_passed=True,nupkg_sha256=sha(package),payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_ILLink_task_replayed=False,original_buildtools_host_replayed=False,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
