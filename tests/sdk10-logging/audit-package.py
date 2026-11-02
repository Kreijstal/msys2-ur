"""Audit configuration archive bytes, original generator layout and retained strict API failure."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
artifact,snapshot,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-sdk10-logging-bootstrap/';base='clang64/lib/dotnet10/library-packs/logging-10.0.2-net10-bootstrap/bin/';manifest=json.loads(files[doc+'payload-sha256.json']);build=json.loads(files[doc+'build-results.json']);archives=json.loads(files[doc+'archives.json']);localization=json.loads(files[doc+'localization-results.json']);api=json.loads(files[doc+'api-results.json']);binary={}
for rel,h in manifest.items():assert sha(files['clang64/'+rel])==h,rel
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+p for p in manifest}|{doc+'payload-sha256.json'}
with tarfile.open(snapshot) as source:
 vmr=json.load(source.extractfile('source-inputs.json'));count=0
 for r in build['projects']:
  assert r['original_production_source_changes']==0
  for rel,h in {**r['original_source_sha256'],**r['original_resource_sha256']}.items():assert sha(source.extractfile('runtime/'+rel).read())==h==vmr['files'][rel]['sha256'],rel
  count+=len(r['original_source_sha256'])
  for ext,h in r['output_sha256'].items():binary[r['assembly']+'.'+ext]=h
 template=source.extractfile('runtime/eng/MultiTargetRoslynComponent.targets.template').read().decode('utf-8-sig')
assert count==177 and len(build['projects'])==7
binary.update(localization['satellite_sha256']);assert {n[len(base):] for n in files if n.startswith(base)}==set(binary)
for rel,h in binary.items():assert sha(files[base+rel])==h,rel
for assembly,a in archives.items():
 data=files['clang64/'+a['archive']];assert sha(data)==a['sha256']
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert sha(z.read(member))==h,member
  md=E.fromstring(z.read(assembly+'.nuspec')).find('metadata');assert md.findtext('id')==assembly and md.findtext('version')=='10.0.2'
  assert md.find('repository').get('commit')=='44525024595742ebe09023abe709df51de65009b';assert md.find('dependencies/group').get('targetFramework')=='net10.0'
  record=next(r for r in build['projects'] if r['assembly']==assembly)
  expected_deps={e['project']:'[10.0.2]' for e in record['original_project_edges'] if e['metadata'].get('ReferenceOutputAssembly','true').lower()!='false'}
  assert {e.get('id'):e.get('version') for e in md.findall('dependencies/group/dependency')}==expected_deps
  for ext,h in record['output_sha256'].items():assert sha(z.read('lib/net10.0/'+assembly+'.'+ext))==h
  if assembly=='Microsoft.Extensions.Options':
   target=z.read('buildTransitive/netstandard2.0/'+assembly+'.targets').decode('utf-8-sig');expected=template.replace('{TargetPrefix}','Microsoft_Extensions_Options').replace('{NuGetPackageId}',assembly).replace('{DisableSourceGeneratorPropertyName}','DisableMicrosoftExtensionsOptionsSourceGenerator');assert target.replace('\r\n','\n').strip()==expected.replace('\r\n','\n').strip()
   for member in z.namelist():
    if member.startswith('analyzers/'):
     assert member.startswith('analyzers/dotnet/roslyn4.4/cs/');rel=member.removeprefix('analyzers/dotnet/roslyn4.4/cs/');assert sha(z.read(member))==binary[rel]
assert len(archives)==6 and all(p['exit_code']==0 for p in api['projects'].values())
assert sum(p['comparison']['expected_entries'] for p in api['projects'].values())==514
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files=len(manifest),original_VMR_files_verified=len(vmr['files']),original_compile_inputs=count,source_binary_symbol_documentation_assets=len(binary),source_archive_sha256=sha(snapshot.read_bytes()),six_exact_NET10_archives_verified=True,original_NS2_Options_analyzer_layout_and_original_packaging_template_verified=True,original_production_source_changes=0,CLR_declarations_checked=514,six_component_strict_CLR_and_nullable_gates_passed=True,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
