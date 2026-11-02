"""Independently audit the Tasks.Extensions4.5.3 native artifact against pinned archives."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,corefx,roslyn,out=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
for p,h in [(corefx,'a4ac86f506488ca48f5b33c4fd0321bcd7b2de17afe0c516bb3879997bc67bbf'),(roslyn,'9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11')]:assert sha(p.read_bytes())==h,p
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-tasksext453-bootstrap/';recipe=Path('mingw-w64-dotnet-tasksext453-bootstrap');source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json']);compiler=json.loads(files[doc+'compiler44-source-inputs.json'])
def original_files(archive,expected,commit):
 with tarfile.open(archive) as t:
  assert t.pax_headers['comment']==commit
  result={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in expected}
 assert {n:sha(b) for n,b in result.items()}==expected;return result
raw=original_files(corefx,source['original_file_sha256'],'637a8d58f72f2b0f1a71187530c3cf433e95a75a')
original_files(roslyn,compiler['original_csc_compile_items'],'1ce8866c9de4c2d67351ef6863699dee03b0804a');assert len(compiler['original_csc_compile_items'])==11 and compiler['original_csc_source_changes']==0
assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0 and audit['unique_original_CSharp_inputs']==8
assert all(c['exit_code']==0 for c in source['commands']+check['commands'])
for k in ['all_original_compile_selections_exact','all_exact_source_reference_and_dependency_bytes_verified','compiler_warning_release_and_netstandard_policy_verified','original_reference_asset_exclusion_and_dependency_groups_preserved','all_original_DLL_XML_empty_marker_version_and_license_assets_preserved']:assert audit[k],k
for k in ['original_identity_dependencies_resources_managed_native_metadata_equal','isolated_exact_old_TasksExtensions_Unsafe_implementations_executed','ValueTask_builder_source_conversion_fault_cancellation_continuation_context_token_and_64_races_passed','fresh_NS2_exact_source_dependency_graph_and_compile_runtime_asset_selection_passed','fresh_NET8_original_empty_framework_marker_consumer_passed']:assert check[k],k
package=files['clang64/lib/dotnet/library-packs/system.threading.tasks.extensions.4.5.3.nupkg'];assert sha(package)==audit['package_sha256']==check['package_sha256'];provenance=json.loads(files[doc+'inputs/published-provenance.json']);assert not provenance['published_DLL_executed_or_used_as_compiler_reference']
assert E.fromstring(raw['src/System.Threading.Tasks.Extensions/pkg/System.Threading.Tasks.Extensions.pkgproj']).findtext('.//{*}ExcludeReferenceAssets')=='true'
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 members_by_path={__import__('urllib.parse',fromlist=['unquote']).unquote(n):n for n in z.namelist()};assert len(members_by_path)==len(z.namelist())
 assert {n for n in members_by_path if n.startswith(('lib/','ref/'))}==set(provenance['original_assets'])
 for n,h in provenance['original_assets'].items():
  if n.endswith('.dll'):
   profile=n.rsplit('/',1)[0];origin='lib/netstandard1.0' if 'portable-' in profile else profile;assert sha(z.read(members_by_path[n]))==source['profiles'][origin]['DLL_sha256'] and sha(z.read(members_by_path[n]))!=h
  else:assert sha(z.read(members_by_path[n]))==h
 assert z.read(members_by_path['lib/portable-net45+win8+wp8+wpa81/System.Threading.Tasks.Extensions.dll'])==z.read('lib/netstandard1.0/System.Threading.Tasks.Extensions.dll')
 md=E.fromstring(z.read('System.Threading.Tasks.Extensions.nuspec')).find('{*}metadata');original=E.fromstring(files[doc+'inputs/original.nuspec']).find('{*}metadata')
 def groups(m):return {g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in m.findall('{*}dependencies/{*}group')}
 assert md.findtext('{*}version')=='4.5.3' and md.find('{*}repository').get('commit')==source['source_commit'] and groups(md)==groups(original)
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==raw[lic]==files['clang64/share/licenses/dotnet-tasksext453-bootstrap/'+lic]
 assert z.read('version.txt')==(source['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==raw['pkg/useSharedDesignerContext.txt']
assert files[doc+'inputs/ManualResetValueTaskSource.cs']==raw['src/Common/tests/System/Threading/Tasks/Sources/ManualResetValueTaskSource.cs']
for n in ['README.md','check.py']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+n]==(recipe/n).read_bytes(),n
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(raw),unique_original_CSharp_inputs=8,production_CSharp_changes=0,original_runtime_profiles=['netstandard1.0','netstandard2.0','portable-net45+win8+wp8+wpa81'],original_API_entries_per_profile=115,original_reference_asset_exclusion_and_dependency_groups_preserved=True,original_DLL_XML_empty_marker_version_and_license_assets_preserved=True,exact_source_reference_and_dependency_bytes_verified=True,portable_alias_byte_identical_to_NS10=True,original_test_source_helper_bytes_verified=True,original_source_csc44_inputs=11,original_metadata_and_isolated_old_ValueTask_behavior_verified=True,fresh_NS2_exact_source_dependency_graph_and_compile_runtime_selection_passed=True,fresh_NET8_original_empty_framework_marker_consumer_passed=True,nupkg_sha256=sha(package),payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
