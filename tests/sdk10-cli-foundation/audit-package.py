"""Audit actual CLI foundation archive payload and source mapping of every binary/symbol."""
from pathlib import Path
import hashlib,json,sys,tarfile
artifact,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact,'r:*') as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
prefix='clang64/';doc=prefix+'share/doc/dotnet-sdk10-cli-foundation-bootstrap/';base=prefix+'lib/dotnet10/build-packs/sdk-cli-foundation-10.0.201-net10-bootstrap/';manifest=json.loads(files[doc+'payload-sha256.json'])
for rel,h in manifest.items():assert sha(files[prefix+rel])==h,rel
assert {n for n in files if n.startswith(prefix)}=={prefix+n for n in manifest}|{doc+'payload-sha256.json'}
records=json.loads(files[doc+'build-results.json']);translations=json.loads(files[doc+'localization-results.json']);assets=json.loads(files[doc+'source-dependency-assets.json']);expected={}
for r in records['projects']:
 for ext,h in r['output_sha256'].items():expected['bin/'+r['assembly']+'.'+ext]=h
for rel,h in translations['satellite_sha256'].items():expected['bin/'+rel]=h
for a in assets:assert a['path'] not in expected,a['path'];expected[a['path']]=a['sha256']
assert {n[len(base):] for n in files if n.startswith(base+'bin/')}==set(expected)
for rel,h in expected.items():assert sha(files[base+rel])==h,rel
resource=json.loads(files[doc+'resource-results.json']);assert resource['exact_values']==966 and resource['satellite_assemblies']==52;assert len(records['projects'])==8;assert b'pkgname = mingw-w64-clang-x86_64-dotnet-sdk10-cli-foundation-bootstrap' in files['.PKGINFO']
e=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_projects=8,original_compile_items=sum(len(r['original_source_sha256']) for r in records['projects']),source_mapped_binary_symbol_and_documentation_assets=len(expected),source_dependency_assets=len(assets),source_native_hostfxr_sha256=expected['bin/x64/hostfxr.dll'],all_payload_and_source_binary_provenance_hashes_match=True,formal_MSBuild_Runtime_NuGet_archive_provided=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(e,indent=2)+'\n');print(json.dumps(e,indent=2))
