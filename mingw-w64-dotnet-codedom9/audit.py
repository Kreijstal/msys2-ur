"""Compare every selected original source/resource input with the pinned archive."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
archive,prepared=(Path(p).resolve() for p in sys.argv[1:]);build=json.loads((prepared/'build/results.json').read_text());expected=dict(build['original_selected_cs_sha256']);expected['src/libraries/System.CodeDom/src/Resources/Strings.resx']=build['original_resource_sha256'];expected['src/libraries/System.CodeDom/src/System.CodeDom.csproj']=build['original_project_sha256'];api=json.loads((prepared/'check/api/results.json').read_text());expected['src/libraries/System.CodeDom/ref/System.CodeDom.cs']=api['original_contract_source_sha256'];plan=json.loads((prepared/'plan/source-inputs.json').read_text());expected['src/libraries/Directory.Build.targets']=plan['original_shared_policy_sha256'];expected['src/libraries/Directory.Build.props']=hashlib.sha256((prepared/'r/src/libraries/Directory.Build.props').read_bytes()).hexdigest();seen=set();resources=[]
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile():continue
  n=m.name.split('/',1)[-1]
  if n.startswith('src/libraries/System.CodeDom/') and Path(n).suffix in {'.resx','.xlf','.xliff','.resources'}:resources.append(n)
  if n in expected:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected);assert resources==['src/libraries/System.CodeDom/src/Resources/Strings.resx']
package=prepared/'feed/system.codedom.9.0.11.nupkg'
with zipfile.ZipFile(package) as z:
 assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/net9.0/System.CodeDom.dll']
 assert z.read('lib/net9.0/System.CodeDom.xml')==(prepared/'documentation/System.CodeDom.xml').read_bytes()
 for n in ['System.CodeDom.dll','System.CodeDom.pdb']:assert z.read('lib/net9.0/'+n)==(prepared/'build'/n).read_bytes()
record=dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,original_resource_members=resources,original_resource_scope_complete=True,localized_resource_sources_present=False,source_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),original_production_cs_changes=0,original_target='net9.0',other_original_framework_profiles_built=False,full_dependency_goal_complete=False);(prepared/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('PASS',len(seen),'original source/project/resource bytes;all original resource scope accounted for')
