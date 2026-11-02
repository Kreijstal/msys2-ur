"""Verify the actual archive payload and source mapping of every tool/runtime binary."""
from pathlib import Path
import hashlib,json,sys,tarfile
artifact,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact,'r:*') as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
prefix='clang64/';doc=prefix+'share/doc/dotnet-nuget73-tasks-bootstrap/';base=prefix+'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/';manifest=json.loads(files[doc+'payload-sha256.json'])
for rel,h in manifest.items():assert sha(files[prefix+rel])==h,rel
assert {n for n in files if n.startswith(prefix)}=={prefix+n for n in manifest}|{doc+'payload-sha256.json'}
records=json.loads(files[doc+'build-results.json']);translations=json.loads(files[doc+'localization-results.json']);assets=json.loads(files[doc+'source-dependency-assets.json']);expected={}
for a in assets:assert a['path'] not in expected;expected[a['path']]=a['sha256']
for r in records['projects']:
 for ext,h in r['output_assets_sha256'].items():expected['bin/'+r['assembly']+'.'+ext]=h
for rel,h in translations['satellite_sha256'].items():expected['bin/'+rel]=h
expected['bin/SdkResolvers/Microsoft.Build.NuGetSdkResolver/Microsoft.Build.NuGetSdkResolver.dll']=expected['bin/Microsoft.Build.NuGetSdkResolver.dll']
# Every binary is an original output or an unchanged installed/source archive asset.
binaries={n[len(base):] for n in files if n.startswith(base) and n.lower().endswith(('.dll','.pdb','.exe'))}
assert binaries<={n for n in expected if n.lower().endswith(('.dll','.pdb','.exe'))}
for rel,h in expected.items():assert sha(files[base+rel])==h,rel
content=json.loads(files[doc+'original-content-sha256.json'])
for rel,h in content.items():assert sha(files[base+'bin/'+Path(rel).name])==h,rel
resources=json.loads(files[doc+'resource-results.json']);assert resources['exact_values']==756 and resources['satellite_assemblies']==39
assert b'pkgname = mingw-w64-clang-x86_64-dotnet-nuget73-tasks-bootstrap' in files['.PKGINFO']
result=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_projects=4,original_compile_items=sum(len(r['original_source_sha256']) for r in records['projects']),source_mapped_binary_assets=len(binaries),source_dependency_assets=len(assets),original_content_files=len(content),all_payload_and_binary_provenance_hashes_match=True,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
