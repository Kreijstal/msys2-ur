"""Audit the final source reference-port package and frozen source/metadata inputs."""
from pathlib import Path
import hashlib,json,sys,tarfile
artifact,roslyn,output=map(Path,sys.argv[1:]);sha=lambda data:hashlib.sha256(data).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-netframework46-contracts-bootstrap/';pack='clang64/lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/';recipe=Path('mingw-w64-dotnet-netframework46-contracts-bootstrap')
record=json.loads(files[doc+'results.json']);compile=json.loads(files[doc+'source-compile-results.json']);check=json.loads(files[doc+'producer-check-results.json']);generation=json.loads(files[doc+'generation-provenance-20261031.json'])
assert record['public_reference_contract_ports'] and record['original_declarative_metadata_restored_and_roundtrip_equal']
assert not record['published_DLL_executed_or_used_as_compiler_reference'] and not record['publisher_implementation_method_bodies_copied']
assert not record['full_original_private_type_layouts_reconstructed']
assert all(c['exit_code']==0 for c in record['commands']+compile['commands']+check['commands'])
assert check['original_public_API_entries']==20541 and check['exact_original_identity_dependencies_and_reference_only_markers']
assert check['typed_consumer_compiler_references_only_source_contracts'] and check['source_NET8_runtime_typed_consumer_passed']
assert not check['original_NET46_runtime_execution_verified']
assert {n for n in files if n.startswith(pack)}=={pack+'mscorlib.dll',pack+'System.Numerics.dll'}
for name,h in record['output_sha256'].items():assert sha(files[pack+name])==h
for name,h in record['generated_source_sha256'].items():assert sha(files[doc+'generated/'+name])==h==sha((recipe/'generated'/name).read_bytes())
for name,h in record['policy_sha256'].items():assert sha(files[doc+'inputs/'+name])==h==sha((recipe/'inputs'/name).read_bytes())
assert generation['generated_CSharp_SHA256']==record['generated_source_sha256']
for name in ['README.md','check.py','generation-provenance-20261031.json']:assert files[doc+name]==(recipe/name).read_bytes()
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
 assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a';verified=set()
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and name in compiler['original_csc_compile_items']:
   assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['SDK-LICENSE.txt','SBRP-LICENSE.txt','ReferenceAssemblies-LICENSE.txt']:assert files['clang64/share/licenses/dotnet-netframework46-contracts-bootstrap/'+name]==files[doc+'inputs/'+name]
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),selected_reference_contracts=['mscorlib/4.0.0.0/b77a5c561934e089','System.Numerics/4.0.0.0/b77a5c561934e089'],original_public_API_entries=20541,complete_public_API_identity_dependencies_and_reference_markers_verified=True,source_compiled_contract_declarative_metadata_roundtrip_equal=True,typed_source_contract_consumer_passed_on_source_NET8_host=True,generated_source_sha256=record['generated_source_sha256'],output_sha256=record['output_sha256'],original_source_csc44_inputs=11,published_DLL_executed_or_used_as_compiler_reference=False,publisher_implementation_method_bodies_copied=False,nonpublic_opaque_support_types=record['nonpublic_opaque_support_types'],full_original_private_type_layouts_reconstructed=False,full_NET46_targeting_pack_built=False,original_NET46_runtime_execution_verified=False,payload_sha256={n:sha(data) for n,data in files.items() if n.startswith('clang64/')},full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
