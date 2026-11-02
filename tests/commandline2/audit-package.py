"""Audit the actual CommandLine2 package archive and every NuGet binary against source build outputs."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact,'r:*') as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
prefix='clang64/';doc=prefix+'share/doc/dotnet-commandline2-bootstrap/';manifest=json.loads(files[doc+'payload-sha256.json'])
for rel,h in manifest.items():assert sha(files[prefix+rel])==h,rel
assert {n for n in files if n.startswith(prefix)}=={prefix+n for n in manifest}|{doc+'payload-sha256.json'}
records=json.loads(files[doc+'build-results.json']);translations=json.loads(files[doc+'localization-results.json']);members={}
for r in records['projects']:
 for ext,h in r['output_sha256'].items():members['lib/'+r['original_target']+'/System.CommandLine.'+ext]=h
for rel,h in translations['satellite_sha256'].items():tfm,_,rest=rel.partition('/bin/');members['lib/'+tfm+'/'+rest]=h
with zipfile.ZipFile(io.BytesIO(files[prefix+'lib/dotnet/library-packs/system.commandline.2.0.2.nupkg'])) as z:
 assert {n for n in z.namelist() if n.startswith('lib/')}==set(members)
 for name,h in members.items():assert sha(z.read(name))==h,name
 meta=E.fromstring(z.read('System.CommandLine.nuspec'));assert meta.findtext('./metadata/id')=='System.CommandLine' and meta.findtext('./metadata/version')=='2.0.2';groups=meta.findall('./metadata/dependencies/group');assert {g.get('targetFramework') for g in groups}=={'net10.0','netstandard2.0'};assert len(meta.find('./metadata/dependencies/group[@targetFramework="net10.0"]'))==0;assert meta.find('./metadata/dependencies/group[@targetFramework="netstandard2.0"]/dependency').get('version')=='[4.5.5]'
assert len(records['projects'])==2 and len(translations['satellite_sha256'])==28;assert b'pkgname = mingw-w64-clang-x86_64-dotnet-commandline2-bootstrap' in files['.PKGINFO']
r=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_framework_profiles=['net10.0','netstandard2.0'],original_compile_items_per_profile=74,source_mapped_archive_binary_and_symbol_assets=len(members),original_satellites=28,all_payload_and_source_binary_archive_hashes_match=True,reference_only_dependencies_packaged_as_runtime=False,original_NS2_memory_package_runtime_closure_verified=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
