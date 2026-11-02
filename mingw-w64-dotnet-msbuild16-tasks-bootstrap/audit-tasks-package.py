"""Independently audit the original Tasks16 bootstrap artifact and source policy."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,msbuild,roslyn,arcade,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(msbuild.read_bytes())=='04907cbf4ade0101998006e955d7c5ca567e19342340ee71fcd36612158c6726'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-msbuild16-tasks-bootstrap/';recipe=Path('mingw-w64-dotnet-msbuild16-tasks-bootstrap')
source=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(msbuild) as t:
 assert t.pax_headers['comment']==source['source_commit']=='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0'
 originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['original_file_sha256']}
assert {n:sha(b) for n,b in originals.items()}==source['original_file_sha256']
assert source['production_CSharp_changes']==audit['production_CSharp_changes']==0
assert audit['original_CSharp_inputs']==202 and audit['original_NS2_feature_guards']
assert audit['all_actual_reference_DLL_bytes_verified_against_source_archives']
assert audit['original_Arcade_CSharp_NoWarn']==['1701','1702','1705','1591']
assert not audit['raw_original_resources_modified_in_place']
for name,item in source['original_Windows_resource_CRLF_projections'].items():
 assert sha(originals[name])==item['original_sha256']
 assert sha(originals[name].replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))==item['Windows_CRLF_projection_sha256']
assert sha(arcade.read_bytes())==source['Arcade_policy_archive_sha256']=='5e731e4cd049e2c71bb376a69e2535c4bb3983fea5870911336db5d564c37180'
with tarfile.open(arcade) as t:
 assert t.pax_headers['comment']==source['Arcade_policy_source_commit']=='26e4b7ad355f3c08eea8296d1733ada986d6edf3'
 policy=t.extractfile(next(m for m in t if m.name.partition('/')[2]==source['Arcade_policy_original_file'])).read()
assert sha(policy)==source['Arcade_policy_original_file_sha256']==audit['Arcade_policy_original_file_sha256']
assert json.loads(originals['global.json'])['msbuild-sdks']['Microsoft.DotNet.Arcade.Sdk']==source['original_Arcade_version_in_global_json']=='1.0.0-beta.19104.18'
manifest=E.fromstring(originals['eng/Version.Details.xml']).find(".//Dependency[@Name='Microsoft.DotNet.Arcade.Sdk']")
assert manifest.get('Version')==source['original_Arcade_version_in_dependency_manifest']=='1.0.0-beta.19101.13'
assert manifest.findtext('Sha')==source['Arcade_policy_source_commit']
assert source['original_Arcade_version_manifest_discrepancy_resolved'] is False
assert checks['original_public_API_entries']==1305 and checks['original_runtime_dependency_identity_sets_equal'] and checks['original_published_resources_verified']
assert checks['original_NS2_PackageReference_consumer'] and checks['all_exact_cached_source_NuGet_archives_verified'] and checks['isolated_all_nine_original_implementations_executed']
assert all(c['exit_code']==0 for c in checks['commands'])
provenance=json.loads(files[doc+'inputs/tasks16-published-provenance.json']);assert not provenance['published_DLL_executed_or_used_as_compiler_reference']
assert sha(files[doc+'inputs/tasks16-published-metadata.json'])==provenance['metadata_baseline_sha256']
assert sha(files[doc+'inputs/tasks16-published-resources.json'])==provenance['resources_baseline_sha256']
resources=json.loads(files[doc+'inputs/tasks16-published-resources.json']);assert len(resources)==11
assert sum(len(v) for v in resources.values() if '$sha256' not in v)==705 and sum('$sha256' in v for v in resources.values())==7
package=files['clang64/lib/dotnet/library-packs/microsoft.build.tasks.core.16.0.461.nupkg'];assert sha(package)==audit['package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 md=E.fromstring(z.read('Microsoft.Build.Tasks.Core.nuspec')).find('{*}metadata')
 assert md.findtext('{*}id')=='Microsoft.Build.Tasks.Core' and md.findtext('{*}version')=='16.0.461'
 assert md.find('{*}repository').get('commit')==source['source_commit']
 assert {d.get('id'):d.get('version') for d in md.findall('.//{*}dependency')}=={n:'['+v+']' for n,v in source['exact_original_dependency_versions'].items()}
 assert sha(z.read('lib/netstandard2.0/Microsoft.Build.Tasks.Core.dll'))==checks['consumer_DLL_sha256']['Microsoft.Build.Tasks.Core']
 for ext in ['dll','xml','pdb']:assert 'lib/netstandard2.0/Microsoft.Build.Tasks.Core.'+ext in z.namelist()
 for license in ['LICENSE','THIRDPARTYNOTICES.txt']:assert z.read(license)==originals[license]==files['clang64/share/licenses/dotnet-msbuild16-tasks-bootstrap/'+license]
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
 assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
 verified=set()
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and name in compiler['original_csc_compile_items']:assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['README.md','check-tasks.py','inputs/Api.cs','inputs/TasksBridge.cs','inputs/TasksCheck.cs','inputs/tasks16-published-metadata.json','inputs/tasks16-published-resources.json','inputs/tasks16-published-provenance.json']:assert files[doc+name]==(recipe/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(originals),original_CSharp_inputs=202,production_CSharp_changes=0,original_public_API_entries=1305,original_runtime_dependency_identities_equal=True,original_resource_strings_verified=705,original_embedded_XML_XSL_files_verified=7,original_Windows_resource_CRLF_projection_inputs=len(source['original_Windows_resource_CRLF_projections']),source_DLL_XML_and_matching_portable_PDB_packaged=True,isolated_all_nine_original_implementations_executed=True,original_Arcade_CSharp_NoWarn_verified=True,original_Arcade_version_manifest_discrepancy_resolved=False,original_NS2_references_pruned_to_BCL=source['original_NS2_references_pruned_to_BCL'],nupkg_sha256=sha(package),original_source_csc44_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},NET472_profile_built=False,original_Arcade_Nerdbank_GenAPI_toolchain_replayed=False,full_upstream_suite_run=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
