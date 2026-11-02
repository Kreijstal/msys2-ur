"""Audit evaluated implementation inputs and preserve the complete original graph."""
from pathlib import Path
import collections,hashlib,json,sys,tarfile
plan=Path(sys.argv[1]).resolve();source=Path(sys.argv[2]).resolve();archive=Path(sys.argv[3]).resolve()
e=json.loads((plan/'evaluated.json').read_text());projects=json.loads((plan/'projects.json').read_text());assert set(e)==set(projects) and len(e)==171
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
original={};missing=[];deps={};external=collections.defaultdict(list);analyzers={};by_project={p['project']:n for n,p in projects.items()}
def relative(native):
 normalized=native.replace('\\','/');marker='/r/';assert marker in normalized,normalized
 return normalized.split(marker,1)[1]
for name,entry in e.items():
 inputs=[]
 for item in entry['items']['Compile']:
  path=relative(item['full_path']);file=source/path
  if file.is_file():original[path]=sha(file);inputs.append(path)
  else:missing.append(dict(assembly=name,path=path))
 original[projects[name]['project']]=sha(source/projects[name]['project'])
 for item in entry['items']['AsnXml']:
  value=item['identity'].replace('\\','/');path=relative(value) if '/r/' in value else (Path(projects[name]['project']).parent/value).as_posix();assert (source/path).is_file(),path;original[path]=sha(source/path)
 ds=[];gs=[]
 for item in entry['items']['ProjectReference']:
  path=relative(item['full_path']);dependency=Path(path).stem
  assert (source/path).is_file(),(name,path)
  if item['metadata'].get('OutputItemType')=='Analyzer':gs.append(dependency);continue
  if item['metadata'].get('ReferenceOutputAssembly','').lower()=='false':continue
  if dependency!='System.Private.CoreLib' and path not in by_project:external[dependency].append(name)
  if dependency not in ds:ds.append(dependency)
 deps[name]=ds
 if gs:analyzers[name]=gs
assert not missing,missing
private_stubs={name:'src/libraries/shims/stubs/'+name+'.csproj' for name in external}
assert len(private_stubs)==19
for name,path in private_stubs.items():assert (source/path).is_file(),(name,path);original[path]=sha(source/path)
for path,digest in json.loads((plan/'source-projects.json').read_text()).items():assert sha(source/path)==digest;original[path]=digest
found={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='081d220c0a773ffb7c6bea6b48727833576a65ef'
 for member in t:
  name=member.name.partition('/')[2]
  if name in original:
   assert member.isfile(),name
   found[name]=hashlib.sha256(t.extractfile(member).read()).hexdigest()
assert found==original,'Evaluated original input differs from pinned archive'
order=[];seen=set()
def visit(name,stack=()):
 if name in seen or name=='System.Private.CoreLib' or name in external:return
 assert name not in stack,('Implementation dependency cycle',stack,name)
 assert name in projects,name
 for dependency in deps[name]:visit(dependency,stack+(name,))
 seen.add(name);order.append(name)
for name in sorted(projects):visit(name)
assert len(order)==171
record=dict(runtime_version='10.0.5',source_commit='081d220c0a773ffb7c6bea6b48727833576a65ef',runtime_archive_sha256=sha(archive),implementation_projects=len(projects),project_kinds=dict(collections.Counter(p['kind'] for p in projects.values())),evaluated_original_compile_items=sum(len(v['items']['Compile']) for v in e.values()),archive_verified_unique_source_and_project_inputs=len(found),all_evaluated_compile_inputs_exist=True,all_evaluated_original_hashes_match_archive=True,compiler_input_stage='Original source/shared project and directory props evaluation. Build-time generator/resource/versioning/ILLink target integration remains required.',dependencies=deps,build_order=order,private_out_of_band_seed_stub_projects=private_stubs,external_shim_dependency_owners=dict(external),explicit_analyzer_projects=analyzers,partial_facade_projects=[n for n,v in e.items() if v['properties']['IsPartialFacadeAssembly']=='true'],asn_xml_generation_inputs=len(e['System.Security.Cryptography']['items']['AsnXml']),remaining=['full original resource/versioning/generator/ILLink build-time target integration','compile original C#/VB implementation graph in recorded dependency order','original private seed stubs and zero-version policies for shims','native framework libraries and full managed/native runtime execution','runtime packaging metadata, SDK10, WindowsDesktop10 and PowerShell7.6','original older dependency/remote/provider/ownership/SQL/desktop/runtime gates'],full_managed_framework10_built=False,full_dependency_goal_complete=False)
(plan/'implementation-plan.json').write_text(json.dumps(record,indent=2)+'\n');(plan/'verified-source-inputs.json').write_text(json.dumps(found,indent=2)+'\n')
print('PASS',len(projects),'original implementation projects,',record['evaluated_original_compile_items'],'source items,',len(found),'archive-verified inputs,19 private seeds,acyclic dependency graph')
