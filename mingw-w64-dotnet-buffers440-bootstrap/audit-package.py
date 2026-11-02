"""Independently audit the final native package and every original asset profile."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,corefx,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(corefx.read_bytes())=='f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-buffers440-bootstrap/';recipe=Path('mingw-w64-dotnet-buffers440-bootstrap')
source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(corefx) as t:
 assert t.pax_headers['comment']==source['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24'
 originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['original_file_sha256']}
assert {n:sha(b) for n,b in originals.items()}==source['original_file_sha256']
assert E.fromstring(originals['Packaging.props']).findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0
assert audit['unique_original_CSharp_inputs']==7
assert all(c['exit_code']==0 for c in source['commands']+check['commands'])
for key in ['all_original_compile_selections_exact','all_exact_source_reference_bytes_verified','compiler_warning_and_release_policy_verified','original_dependency_groups_and_Compile_exclusions_preserved','all_original_DLL_XML_framework_marker_version_and_license_assets_preserved']:assert audit[key],key
for key in ['original_identity_dependencies_resources_and_managed_native_metadata_equal','isolated_exact_old_implementations_executed','pool_boundary_reuse_clearing_errors_exhaustion_overlimit_and_8000_concurrent_ownership_checks_per_runtime','original_EventSource_payloads_delivered_in_each_runtime_profile','fresh_NS2_exact_reference_and_runtime_consumer_passed','fresh_NET8_original_empty_framework_marker_consumer_passed']:assert check[key],key
assert check['original_public_API_entries_per_profile']==8
assert set(source['profiles'])=={'lib/netstandard1.1','lib/netstandard2.0','ref/netstandard1.1','ref/netstandard2.0'}
for profile,p in source['profiles'].items():
 original='src/System.Buffers/'+('src' if profile.startswith('lib/') else 'ref')+'/System.Buffers.csproj'
 assert len(p['original_CSharp_inputs'])==len(E.fromstring(originals[original]).findall('.//{*}Compile'))+(1 if profile.startswith('lib/') else 0)
provenance=json.loads(files[doc+'inputs/published-provenance.json']);documentation=json.loads(files[doc+'inputs/documentation-provenance.json'])
assert not provenance['published_DLL_executed_or_used_as_compiler_reference'] and not documentation['published_DLL_executed_or_used_as_compiler_reference']
package=files['clang64/lib/dotnet/library-packs/system.buffers.4.4.0.nupkg'];assert sha(package)==audit['package_sha256']==check['exact_package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 md=E.fromstring(z.read('System.Buffers.nuspec')).find('{*}metadata');assert md.findtext('{*}version')=='4.4.0' and md.find('{*}repository').get('commit')==source['source_commit']
 groups={g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')}
 assert groups==provenance['original_dependency_attributes']
 for profile,p in source['profiles'].items():
  assert sha(z.read(profile+'/System.Buffers.dll'))==p['DLL_sha256']
  name=profile+'/System.Buffers.xml';assert sha(z.read(name))==documentation['XML_asset_sha256'][name] and z.read(name)==files[doc+'inputs/System.Buffers.xml']
 for kind in ['lib','ref']:assert z.read(kind+'/netcoreapp2.0/_._')==b''
 assert z.read('version.txt')==(source['source_commit']+'\r\n').encode();assert z.read('useSharedDesignerContext.txt')==originals['pkg/useSharedDesignerContext.txt']==b''
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==originals[lic]==files['clang64/share/licenses/dotnet-buffers440-bootstrap/'+lic]
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
 assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
 verified=set()
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and name in compiler['original_csc_compile_items']:
   assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['README.md','check.py']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+name]==(recipe/name).read_bytes(),name
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(originals),production_CSharp_changes=0,unique_original_CSharp_inputs=7,profiles=audit['profiles'],original_public_API_entries_per_profile=8,original_identity_dependencies_resources_and_managed_native_metadata_equal=True,original_dependency_groups_and_Compile_exclusions_preserved=True,all_original_DLL_XML_framework_marker_version_and_license_assets_preserved=True,original_SkipValidatePackageTargetFramework_translated_to_NU5128=True,original_documentation_text_imported_from_hash_pinned_published_package=True,isolated_NS11_NS2_pool_behavior_concurrency_and_EventSource_checks_passed=True,fresh_NS2_exact_reference_runtime_consumer_passed=True,fresh_NET8_framework_marker_consumer_passed=True,nupkg_sha256=sha(package),original_source_csc44_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
