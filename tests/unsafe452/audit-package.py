"""Independently audit the final native package against pinned source archives."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,corefx,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(corefx.read_bytes())=='f8043a5f7853d2b667f75a3e530ba7b5e9c1a6651949d0ce2a00c044a6697b54'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-unsafe452-bootstrap/';recipe=Path('mingw-w64-dotnet-unsafe452-bootstrap')
source=json.loads(files[doc+'results.json']);audit=json.loads(files[doc+'producer-audit.json']);check=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(corefx) as t:
 assert t.pax_headers['comment']==source['source_commit']=='02b11eeee1fbc5f3ef43a1452fe07efd25fa1715'
 originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in source['original_file_sha256']}
assert {n:sha(b) for n,b in originals.items()}==source['original_file_sha256']
assert source['production_source_changes']==audit['production_source_changes']==0
assert all(c['exit_code']==0 for c in source['commands']+check['commands'])
for key in ['all_original_runtime_and_reference_profiles_preserved','original_dependency_groups_preserved','original_XML_and_license_bytes_preserved','original_native_VERSIONINFO_preserved','original_IL_and_CSharp_source_hashes_verified']:assert audit[key],key
for key in ['all_original_public_IL_method_bodies_equal','all_34_public_methods_executed_in_each_runtime_profile','all_native_VERSIONINFO_fields_equal','isolated_exact_old_implementation_executed','fresh_NS2_PackageReference_consumer_passed']:assert check[key],key
assert check['original_public_API_entries_per_profile']==35
assert set(source['profiles'])=={'netstandard1.0','netstandard2.0','netcoreapp2.0'} and set(source['reference_profiles'])=={'netstandard1.0','netstandard2.0'}
package=files['clang64/lib/dotnet/library-packs/system.runtime.compilerservices.unsafe.4.5.2.nupkg']
assert sha(package)==audit['package_sha256']==check['exact_package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
 md=E.fromstring(z.read('System.Runtime.CompilerServices.Unsafe.nuspec')).find('{*}metadata')
 assert md.findtext('{*}version')=='4.5.2' and md.find('{*}repository').get('commit')==source['source_commit']
 for tfm,p in source['profiles'].items():
  assert sha(z.read('lib/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll'))==p['DLL_sha256']
  assert z.read('lib/'+tfm+'/System.Runtime.CompilerServices.Unsafe.xml')==originals['src/System.Runtime.CompilerServices.Unsafe/src/System.Runtime.CompilerServices.Unsafe.xml']
 for tfm,p in source['reference_profiles'].items():assert sha(z.read('ref/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll'))==p['output_sha256']
 for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:assert z.read(lic)==originals[lic]==files['clang64/share/licenses/dotnet-unsafe452-bootstrap/'+lic]
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
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=source['source_commit'],original_source_files_verified=len(originals),production_source_changes=0,original_runtime_profiles=list(source['profiles']),original_reference_profiles=list(source['reference_profiles']),original_API_entries_per_profile=35,all_34_public_IL_bodies_equal_and_executed_in_each_runtime_profile=True,all_original_native_VERSIONINFO_and_managed_versions_preserved=True,fresh_NS2_exact_reference_runtime_consumer_passed=True,original_dependency_groups_preserved=True,nupkg_sha256=sha(package),original_source_csc44_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_buildtools_host_replayed=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
