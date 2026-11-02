"""Audit NuGet6.13.2 archive payload, source provenance and unchanged package requirements."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,source_archive,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-nuget6132-template-bootstrap/';base='clang64/lib/dotnet10/library-packs/nuget-6.13.2-net10-template-bootstrap/bin/';manifest=json.loads(files[doc+'payload-sha256.json']);records=json.loads(files[doc+'build-results.json']);source_inputs=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'source-audit.json']);archives=json.loads(files[doc+'archives.json']);requirements=json.loads(files[doc+'dependency-restore-results.json'])['original_requirements'];count=0
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+p for p in manifest}|{doc+'payload-sha256.json'}
for rel,h in manifest.items():assert sha(files['clang64/'+rel])==h,rel
with tarfile.open(source_archive) as t:
 def source(rel):return t.extractfile('NuGet.Client-5d81cb8da82eda8a6b47aae92d1e6f888de982ce/'+rel).read()
 for rel,h in source_inputs['original_project_inputs_sha256'].items():assert sha(source(rel))==h,rel
 for r in records['projects']:
  assert r['original_target']=='net10.0' and r['original_version']=='6.13.2' and r['assembly_version']==r['file_version']=='6.13.2.1' and r['original_production_source_changes']==0
  for rel,h in {**r['original_source_sha256'],**r['original_resource_sha256']}.items():assert sha(source(rel))==h,rel
  count+=len(r['original_source_sha256']);assembly=r['assembly'];a=archives[assembly];data=files['clang64/'+a['archive']];assert sha(data)==a['sha256']
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   assert set(z.namelist())==set(a['members'])
   for member,h in a['members'].items():assert sha(z.read(member))==h,member
   meta=E.fromstring(z.read(assembly+'.nuspec')).find('metadata');assert meta.findtext('id')==assembly and meta.findtext('version')=='6.13.2';assert meta.find('repository').get('commit')=='5d81cb8da82eda8a6b47aae92d1e6f888de982ce';assert meta.find('dependencies/group').get('targetFramework')=='net10.0'
   project=E.fromstring(source('src/NuGet.Core/'+assembly+'/'+assembly+'.csproj'));expected={Path(p.get('Include').replace('\\','/')).stem:'[6.13.2]' for p in project.iter('ProjectReference')}
   expected.update({p['identity']:requirements[p['identity']] for p in r['declared_package_references']});assert {p.get('id'):p.get('version') for p in meta.findall('dependencies/group/dependency')}==expected
   for ext in ['dll','pdb','xml']:
    member='lib/net10.0/'+assembly+'.'+ext;assert sha(z.read(member))==sha(files[base+assembly+'.'+ext])==audit['production_output_sha256'][assembly+'.'+ext]
assert len(archives)==7 and count==970 and len(audit['production_output_sha256'])==21
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_archive_sha256=sha(source_archive.read_bytes()),payload_files=len(manifest),original_compile_items=count,unique_original_compile_inputs=audit['unique_original_compile_inputs'],source_inputs_verified=audit['selected_original_archive_inputs_verified'],source_binary_symbol_documentation_assets=21,seven_original_NuGet6132_NET10_archives_and_dependency_requirements_verified=True,original_production_source_changes=0,other_original_framework_profiles_built=False,external_localization_package_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
