"""Compare every selected original source/resource input with the pinned archive."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
archive,prepared=(Path(p).resolve() for p in sys.argv[1:]);build=json.loads((prepared/'build/results.json').read_text());expected=dict(build['original_selected_cs_sha256']);expected['src/libraries/System.Reflection.MetadataLoadContext/src/Resources/Strings.resx']=build['original_resource_sha256'];expected['src/libraries/System.Reflection.MetadataLoadContext/src/System.Reflection.MetadataLoadContext.csproj']=build['original_project_sha256'];api=json.loads((prepared/'check/api/results.json').read_text());expected['src/libraries/System.Reflection.MetadataLoadContext/ref/System.Reflection.MetadataLoadContext.cs']=api['original_contract_source_sha256'];plan=json.loads((prepared/'plan/source-inputs.json').read_text());expected['src/libraries/Directory.Build.targets']=plan['original_shared_policy_sha256'];expected['src/libraries/Directory.Build.props']=hashlib.sha256((prepared/'r/src/libraries/Directory.Build.props').read_bytes()).hexdigest();expected['eng/Versions.props']=hashlib.sha256((prepared/'r/eng/Versions.props').read_bytes()).hexdigest();expected['src/libraries/NetCoreAppLibrary.props']=hashlib.sha256((prepared/'r/src/libraries/NetCoreAppLibrary.props').read_bytes()).hexdigest();seen=set();resources=[]
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile():continue
  n=m.name.split('/',1)[-1]
  if n.startswith('src/libraries/System.Reflection.MetadataLoadContext/') and Path(n).suffix in {'.resx','.xlf','.xliff','.resources'}:resources.append(n)
  if n in expected:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected);assert resources==['src/libraries/System.Reflection.MetadataLoadContext/src/Resources/Strings.resx']
package=prepared/'feed/system.reflection.metadataloadcontext.9.0.11.nupkg'
with zipfile.ZipFile(package) as z:
 assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/net9.0/System.Reflection.MetadataLoadContext.dll']
 assert z.read('lib/net9.0/System.Reflection.MetadataLoadContext.xml')==(prepared/'documentation/System.Reflection.MetadataLoadContext.xml').read_bytes()
 for n in ['System.Reflection.MetadataLoadContext.dll','System.Reflection.MetadataLoadContext.pdb']:assert z.read('lib/net9.0/'+n)==(prepared/'build'/n).read_bytes()
record=dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,original_resource_members=resources,original_resource_scope_complete=True,localized_resource_sources_present=False,source_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),original_production_cs_changes=0,original_target='net9.0',other_original_framework_profiles_built=False,full_dependency_goal_complete=False);(prepared/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('PASS',len(seen),'original source/project/resource bytes;all original resource scope accounted for')
