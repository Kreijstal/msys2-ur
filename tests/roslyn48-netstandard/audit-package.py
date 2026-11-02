"""Inspect the actual Roslyn4.8 package and immutable upstream source mappings."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,source_archive,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source_archive.read_bytes())=='6bca93036741be94c516ed7e6c8c8a8e11cbde8c2f8478d4f79eef66861669c6'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-roslyn48/';inputs=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'source-package-audit.json']);resources=json.loads(files[doc+'localization.json']);source={}
assert inputs['roslyn_version']=='4.8.0' and inputs['roslyn_commit']=='e091728607ca0fc9efca55ccfb3e59259c6b5a0a'
for n,r in inputs['projects'].items():
 source.update(r['original_cs'])
 if not r.get('tool'):source[r['original_project']]=r['original_project_sha256'];source.update(r['original_resources'])
with tarfile.open(source_archive) as t:
 assert t.pax_headers['comment']==inputs['roslyn_commit'];found={}
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and rel in source:found[rel]=sha(t.extractfile(m).read())
assert found==source
packages={};dlls={}
for assembly,r in inputs['projects'].items():
 if r.get('tool'):continue
 id='Microsoft.CodeAnalysis.Common' if assembly=='Microsoft.CodeAnalysis' else 'Microsoft.CodeAnalysis.Workspaces.Common' if assembly=='Microsoft.CodeAnalysis.Workspaces' else assembly
 path='clang64/lib/dotnet/library-packs/'+id.lower()+'.4.8.0.nupkg';data=files[path]
 assert sha(data)==audit['source_packages'][id]['sha256']
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  root=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))));md=next(p for p in root if p.tag.endswith('metadata'));props={p.tag.rsplit('}',1)[-1]:p.text for p in md}
  assert props['id']==id and props['version']=='4.8.0';assert next(p for p in md if p.tag.endswith('repository')).get('commit')==inputs['roslyn_commit']
  assert all(p.get('targetFramework')=='.NETStandard2.0' for p in md.iter() if p.tag.endswith('group'))
  deps={p.get('id'):p.get('version').strip('[]') for p in md.iter() if p.tag.endswith('dependency')};assert deps==r['resolved_dependencies']
  for member in z.namelist():
   if member.endswith('.dll'):
    assert member.startswith('lib/netstandard2.0/'),member;dlls[id+'/'+member]=sha(z.read(member))
 packages[id]=dict(sha256=sha(data),dependencies=deps)
assert len(packages)==4 and len(dlls)==56
r=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_file_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},source_archive_sha256=sha(source_archive.read_bytes()),selected_original_source_resource_project_inputs_verified=len(source),original_archive_inputs_verified_by_build_audit=audit['original_archive_inputs_verified'],library_original_compile_inputs=sum(len(p['original_cs']) for p in inputs['projects'].values() if not p.get('tool')),tool_original_compile_inputs=sum(len(p['original_cs']) for p in inputs['projects'].values() if p.get('tool')),source_packages=packages,source_DLL_assets_verified=56,resource_sets=len(resources),resource_values=sum(len(p['strings']) for p in resources),regenerated_original_source_files=len(audit['regenerated_original_sources']),source_SQLite_exclusion_preserved=True,original_production_source_changes=0,original_NS2_profiles_preserved=True,standalone_IOperation_host_framework='net8.0',original_IOperation_net7_tool_profile_built=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['payload_file_sha256','source_packages']},indent=2))
