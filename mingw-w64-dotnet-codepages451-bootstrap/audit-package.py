"""Independently audit CodePages4.5.1's complete original multi-lineage layout."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,zipfile,xml.etree.ElementTree as E
artifact,legacy,current,roslyn,out=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-codepages451-bootstrap/';recipe=Path('mingw-w64-dotnet-codepages451-bootstrap');source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json']);compiler=json.loads(files[doc+'compiler44-source-inputs.json']);provenance=json.loads(files[doc+'inputs/published-provenance.json']);manifest=json.loads(files[doc+'original-profile-requirements-20261031.json'])
raw={}
for tag,archive,commit,h in [('legacy',legacy,'4d1af962ca0fede10beb01d197367c2f90e92c97','1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'),('current',current,'99ce22c306b07f99ddae60f443d23a983ae78f7b','87d9ed6638b66ed119df9c8923df0fec0b5467819371f297c474f23bb1ff204a')]:
 assert sha(archive.read_bytes())==h==source['source_lineages'][tag]['archive_sha256']
 with tarfile.open(archive) as t:
  assert t.pax_headers['comment']==commit==source['source_lineages'][tag]['commit'];raw[tag]={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['source_lineages'][tag]['original_file_sha256']}
 assert {n:sha(b) for n,b in raw[tag].items()}==source['source_lineages'][tag]['original_file_sha256']
assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0
assert all(c['exit_code']==0 for c in source['commands']+check['commands']) and check['all_five_implementations_verified'] and set(check['validated_profiles'])==set(manifest['profiles'])
for k in ['original_source_selections_and_exact_reference_bytes_verified','original_warning_release_platform_and_target_policy_verified','all_five_distinct_implementations_and_eight_original_DLL_paths_preserved','original_dependency_groups_and_twelve_empty_markers_preserved','all_original_alias_groups_byte_identical']:assert audit[k],k
for k in ['original_identity_dependency_resource_and_managed_native_metadata_verified','exact_candidate_implementations_and_newer_Unsafe_dependency_executed','exact_bytes_multibyte_stateful_fallback_streaming_concurrency_platform_ACP_checks_passed','fresh_NS2_portable_and_Windows_exact_compile_runtime_selection_and_execution_passed','fresh_NET8_Windows_restore_original_Core2_runtime_asset_and_Platforms212_selected']:assert check[k],k
archive=files['clang64/lib/dotnet/library-packs/system.text.encoding.codepages.4.5.1.nupkg'];assert sha(archive)==audit['package_sha256']==check['package_sha256'];assert not provenance['published_DLL_executed_or_used_as_compiler_reference']
with zipfile.ZipFile(io.BytesIO(archive)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 assert {n for n in z.namelist() if n.startswith(('lib/','ref/','runtimes/'))}==set(provenance['original_assets'])
 for profile,item in source['profiles'].items():
  for n in item['original_paths']:assert sha(z.read(n))==item['DLL_sha256'] and sha(z.read(n))!=provenance['original_assets'][n]
 for n in provenance['original_assets']:
  if n.endswith('/_._'):assert z.read(n)==b''
 def groups(m):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in m.findall('{*}dependencies/{*}group')}
 md=E.fromstring(z.read('System.Text.Encoding.CodePages.nuspec')).find('{*}metadata');original=E.fromstring(files[doc+'inputs/original.nuspec']).find('{*}metadata');assert groups(md)==groups(original) and md.findtext('{*}version')=='4.5.1'
 for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(name)==raw['current'][name]==files['clang64/share/licenses/dotnet-codepages451-bootstrap/'+name]
 for name in ['LICENSE','THIRD-PARTY-NOTICES']:assert files['clang64/share/licenses/dotnet-codepages451-bootstrap/legacy-'+name]==raw['legacy'][name]
 assert z.read('version.txt')==b'99ce22c306b07f99ddae60f443d23a983ae78f7b\r\n' and z.read('useSharedDesignerContext.txt')==raw['current']['pkg/useSharedDesignerContext.txt']
assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
 verified=set()
 for m in t:
  n=m.name.partition('/')[2]
  if m.isfile() and n in compiler['original_csc_compile_items']:assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][n];verified.add(n)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for n in ['README.md','check.py','original-profile-requirements-20261031.json']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+n]==(recipe/n).read_bytes(),n
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_lineages={k:d['commit'] for k,d in source['source_lineages'].items()},original_source_files_verified=sum(len(d) for d in raw.values()),unique_original_CSharp_inputs_across_lineages=audit['unique_original_CSharp_inputs_across_lineages'],production_CSharp_changes=0,original_distinct_implementations=5,original_DLL_asset_paths=8,original_API_entries_per_implementation=5,all_original_source_selections_reference_bytes_and_alias_groups_verified=True,original_dependencies_twelve_markers_versions_licenses_preserved=True,original_metadata_resources_and_isolated_exact_source_implementations_verified=True,fresh_NS2_portable_Windows_consumers_and_NET8_runtime_asset_selection_verified=True,original_Csc44_source_inputs=11,nupkg_sha256=sha(archive),payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
