"""Audit the task package archive, including every binary's source output/archive mapping."""
from pathlib import Path
import hashlib,json,sys,tarfile
artifact,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact,'r:*') as t:
 files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
prefix='clang64/';doc=prefix+'share/doc/dotnet-sdk10-tasks-bootstrap/';base=prefix+'lib/dotnet10/build-packs/sdk-10.0.201-net10-bootstrap/';manifest=json.loads(files[doc+'payload-sha256.json'])
for rel,h in manifest.items():assert sha(files[prefix+rel])==h,rel
assert {n for n in files if n.startswith(prefix)}=={prefix+n for n in manifest}|{doc+'payload-sha256.json'}
records=json.loads(files[doc+'build-results.json']);localization=json.loads(files[doc+'localization-results.json']);assets=json.loads(files[doc+'source-dependency-assets.json']);expected={}
for r in records['projects']:
 for ext,h in r['output_sha256'].items():expected['bin/'+r['assembly']+'.'+ext]=h
for rel,h in localization['satellite_sha256'].items():expected['bin/'+rel]=h
for asset in assets:
 rel=asset['path'];assert rel not in expected,rel;expected[rel]=asset['sha256']
assert {n[len(base):] for n in files if n.startswith(base+'bin/')}==set(expected)
for rel,h in expected.items():assert sha(files[base+rel])==h,rel
content=json.loads(files[doc+'original-content-sha256.json'])
for rel,h in content.items():assert sha(files[base+'original-content/'+rel])==h,rel
assert all(not p.lower().endswith(('.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources')) for p in content)
resources=json.loads(files[doc+'resource-results.json']);assert resources['exact_values']==7672 and resources['satellite_assemblies']==78
assert b'pkgname = mingw-w64-clang-x86_64-dotnet-sdk10-tasks-bootstrap' in files['.PKGINFO']
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_projects=len(records['projects']),original_compile_items=sum(len(r['original_source_sha256']) for r in records['projects']),source_mapped_binary_and_symbol_assets=len(expected),source_dependency_assets=len(assets),original_content_files=len(content),all_payload_and_binary_provenance_hashes_match=True,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
