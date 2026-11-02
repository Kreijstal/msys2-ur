"""Independently audit the final Vectors4.4 native package and pinned source inputs."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,urllib.parse,xml.etree.ElementTree as E,zipfile
artifact,corefx,roslyn,output=map(Path,sys.argv[1:]);sha=lambda data:hashlib.sha256(data).hexdigest();assert sha(corefx.read_bytes())=='f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-vectors440-bootstrap/';recipe=Path('mingw-w64-dotnet-vectors440-bootstrap');source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(corefx) as t:
 assert t.pax_headers['comment']==source['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24'
 originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['original_file_sha256']}
assert {n:sha(b) for n,b in originals.items()}==source['original_file_sha256'];assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0
assert all(c['exit_code']==0 for c in source['commands']+check['commands'])
for key in ['original_SkipValidatePackageTargetFramework_translated_to_NU5128_NU5130','original_compile_selections_and_reference_bytes_verified','NET46_reference_projection_replayed_and_equal','original_dependency_groups_preserved','all_seven_original_DLL_and_XML_profiles_preserved','all_fourteen_original_empty_markers_preserved','portable_alias_DLL_byte_identical_to_NS10']:assert audit[key],key
for key in ['original_identity_dependencies_resources_and_managed_native_metadata_equal','isolated_exact_old_implementations_executed','ten_generic_scalar_types_and_vector_matrix_quaternion_plane_checks_passed','all_seven_original_NET46_forwarders_verified','fresh_NS2_exact_reference_and_runtime_consumer_passed','fresh_NET8_original_empty_framework_marker_consumer_passed']:assert check[key],key
assert check['original_public_API_entries_per_portable_profile']==497 and check['original_public_API_entries_per_NET46_profile']==133
assert len(source['profiles'])==6
package=files['clang64/lib/dotnet/library-packs/system.numerics.vectors.4.4.0.nupkg'];assert sha(package)==audit['package_sha256']==check['exact_package_sha256'];provenance=json.loads(files[doc+'inputs/published-provenance.json'])
assert not provenance['published_DLL_executed_or_used_as_compiler_reference']
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members'];members={urllib.parse.unquote(n):n for n in z.namelist()};assert len(members)==len(z.namelist())
 for n in provenance['DLL_asset_sha256']:
  path=urllib.parse.unquote(n)
  if 'portable-' not in path:assert sha(z.read(members[path]))==source['profiles'][path.rsplit('/',1)[0]]['DLL_sha256']
 assert z.read(members['lib/portable-net45+win8+wp8+wpa81/System.Numerics.Vectors.dll'])==z.read(members['lib/netstandard1.0/System.Numerics.Vectors.dll'])
 for n,h in provenance['XML_asset_sha256'].items():assert sha(z.read(members[urllib.parse.unquote(n)]))==h
 for n in provenance['empty_markers']:assert z.read(members[n])==b''
 md=E.fromstring(z.read('System.Numerics.Vectors.nuspec')).find('{*}metadata');assert md.findtext('{*}version')=='4.4.0' and md.find('{*}repository').get('commit')==source['source_commit']
 groups={g.get('targetFramework'):[{k:(v.removeprefix('[').removesuffix(', )') if k=='version' else v) for k,v in d.attrib.items()} for d in g] for g in md.findall('{*}dependencies/{*}group')};assert groups==provenance['original_dependency_attributes']
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==originals[lic]==files['clang64/share/licenses/dotnet-vectors440-bootstrap/'+lic]
 assert z.read('version.txt')==(source['source_commit']+'\r\n').encode() and z.read('useSharedDesignerContext.txt')==originals['pkg/useSharedDesignerContext.txt']
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
 verified=set()
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and name in compiler['original_csc_compile_items']:
   assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['README.md','check.py']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+name]==(recipe/name).read_bytes(),name
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(originals),production_CSharp_changes=0,unique_original_CSharp_inputs=audit['unique_original_CSharp_inputs'],profiles=audit['profiles'],original_API_entries_per_portable_profile=497,original_API_entries_per_NET46_profile=133,all_seven_original_NET46_forwarders_preserved=True,original_compile_selections_and_exact_source_reference_bytes_verified=True,NET46_reference_source_projection_removes_only_seven_forwarded_structs=True,all_seven_original_DLL_and_XML_profiles_preserved=True,all_fourteen_original_empty_markers_preserved=True,portable_alias_byte_identical_to_NS10=True,original_dependency_groups_preserved=True,ten_generic_scalar_types_and_geometry_runtime_checks_passed=True,fresh_NS2_exact_reference_runtime_consumer_passed=True,fresh_NET8_framework_marker_consumer_passed=True,original_source_csc44_inputs=11,nupkg_sha256=sha(package),payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_upstream_suite_run=False,historical_NET46_runtime_execution_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
