"""Independently audit the selected NETCore2.0 reference package and source inputs."""
from pathlib import Path
import hashlib,json,sys,tarfile
artifact,corefx,roslyn,out=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(corefx.read_bytes())=='f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
assert sha(roslyn.read_bytes())=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-netcore20-contracts-bootstrap/';pack='clang64/lib/dotnet/reference-packs/netcore20-contracts-bootstrap/ref/';recipe=Path('mingw-w64-dotnet-netcore20-contracts-bootstrap')
s=json.loads(files[doc+'results.json']);a=json.loads(files[doc+'producer-audit.json']);f=json.loads(files[doc+'facade-results.json']);c=json.loads(files[doc+'producer-check-results.json']);compiler=json.loads(files[doc+'compiler44-source-inputs.json'])
with tarfile.open(corefx) as t:
 assert t.pax_headers['comment']==s['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24'
 raw={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in s['original_file_sha256']}
assert {n:sha(b) for n,b in raw.items()}==s['original_file_sha256'];assert s['original_CSharp_changes']==a['original_CSharp_changes']==0
assert a['source_contracts']==9 and a['original_API_entries']==c['original_API_entries']==10936
assert a['original_compile_selections_and_source_dependency_reference_bytes_verified'] and a['original_reference_warning_policy_preserved']
assert all(x['exit_code']==0 for x in s['commands']+f['commands']+c['commands'])
assert c['original_reference_identity_dependencies_and_API_verified'] and c['original_facade_2417_forwarders_86_scopes_verified'] and c['typed_consumer_only_source_references_and_original_Unsafe_NS2_reference_compiled'] and c['typed_consumer_source_NET8_runtime_passed']
assert set(n.removeprefix(pack) for n in files if n.startswith(pack))==set(a['reference_DLL_sha256']) and len(a['reference_DLL_sha256'])==10
for n,h in a['reference_DLL_sha256'].items():assert sha(files[pack+n])==h
assert sha(files[pack+'netstandard.dll'])==f['facade_sha256'];assert f['original_forwarders']==2417 and f['original_reference_scopes']==86
assert not f['published_DLL_executed_or_used_as_compiler_reference'] and not f['published_implementation_bodies_copied']
assert f['source_helper_sha256']==sha(files[doc+'inputs/FacadePort.cs']) and f['declarative_metadata_sha256']==sha(files[doc+'inputs/netstandard20-forwarders.json'])
with tarfile.open(roslyn) as t:
 checked=set()
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and name in compiler['original_csc_compile_items']:assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];checked.add(name)
assert len(checked)==11 and compiler['original_csc_source_changes']==0
for n in ['README.md','check.py']+[p.relative_to(recipe).as_posix() for p in (recipe/'inputs').iterdir() if p.is_file()]:assert files[doc+n]==(recipe/n).read_bytes(),n
for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert files['clang64/share/licenses/dotnet-netcore20-contracts-bootstrap/'+lic]==raw[lic]
assert not any(n.endswith('.nupkg') for n in files)
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=s['source_commit'],original_source_files_verified=len(raw),unique_original_CSharp_inputs=a['unique_original_CSharp_inputs'],original_CSharp_changes=0,source_contracts=9,original_API_entries=10936,source_reference_DLLs=10,original_reference_identity_dependencies_and_API_verified=True,original_reference_warning_policy_preserved=True,complete_original_facade_forwarders=2417,complete_original_facade_reference_scopes=86,facade_is_explicit_source_metadata_port=True,published_implementation_bodies_copied=False,published_DLL_executed_or_used_as_compiler_reference=False,typed_consumer_original_Unsafe_NS2_reference_binding_verified=True,typed_consumer_source_NET8_runtime_verified=True,original_Csc44_source_inputs=11,NuGet_runtime_archives_installed=0,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},complete_NETCore2_targeting_pack_registered=False,original_NETCore2_runtime_execution_verified=False,original_buildtools_host_replayed=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
