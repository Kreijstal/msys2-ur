"""Compare every selected original source/resource input with the pinned archive."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
archive,prepared=(Path(p).resolve() for p in sys.argv[1:]);build=json.loads((prepared/'build/results.json').read_text());expected=dict(build['original_selected_cs_sha256']);expected['src/libraries/System.Security.Cryptography.Xml/src/Resources/Strings.resx']=build['original_resource_sha256'];expected['src/libraries/System.Security.Cryptography.Xml/src/System.Security.Cryptography.Xml.csproj']=build['original_project_sha256'];api=json.loads((prepared/'check/api/results.json').read_text());expected['src/libraries/System.Security.Cryptography.Xml/ref/System.Security.Cryptography.Xml.cs']=api['original_contract_source_sha256'];plan=json.loads((prepared/'plan/source-inputs.json').read_text());expected['src/libraries/Directory.Build.targets']=plan['original_shared_policy_sha256'];expected['src/libraries/Directory.Build.props']=hashlib.sha256((prepared/'r/src/libraries/Directory.Build.props').read_bytes()).hexdigest();expected['eng/Versions.props']=hashlib.sha256((prepared/'r/eng/Versions.props').read_bytes()).hexdigest();expected['src/libraries/NetCoreAppLibrary.props']=hashlib.sha256((prepared/'r/src/libraries/NetCoreAppLibrary.props').read_bytes()).hexdigest();seen=set();resources=[];test_resources=[]
for name in ['src/libraries/System.Security.Cryptography.Xml/ref/System.Security.Cryptography.Xml.csproj','src/libraries/System.Security.Cryptography.Xml/Directory.Build.props','src/libraries/System.Security.Cryptography.Xml/src/CompatibilitySuppressions.xml']:
 expected[name]=hashlib.sha256((prepared/'r'/name).read_bytes()).hexdigest()
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile():continue
  n=m.name.split('/',1)[-1]
  if n.startswith('src/libraries/System.Security.Cryptography.Xml/') and Path(n).suffix in {'.resx','.xlf','.xliff','.resources'}:
   (test_resources if 'tests' in Path(n).parts or 'test' in Path(n).parts else resources).append(n)
  if n in expected:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected);assert resources==['src/libraries/System.Security.Cryptography.Xml/src/Resources/Strings.resx']
package=prepared/'feed/system.security.cryptography.xml.9.0.11.nupkg'
with zipfile.ZipFile(package) as z:
 assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/net9.0/System.Security.Cryptography.Xml.dll']
 assert z.read('lib/net9.0/System.Security.Cryptography.Xml.xml')==(prepared/'documentation/System.Security.Cryptography.Xml.xml').read_bytes()
 for n in ['System.Security.Cryptography.Xml.dll','System.Security.Cryptography.Xml.pdb']:assert z.read('lib/net9.0/'+n)==(prepared/'build'/n).read_bytes()
record=dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,original_resource_members=resources,original_test_resource_members=test_resources,original_resource_scope_complete=True,localized_resource_sources_present=False,source_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),original_production_cs_changes=0,original_target='net9.0',other_original_framework_profiles_built=False,full_dependency_goal_complete=False);(prepared/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('PASS',len(seen),'original source/project/resource bytes;all original resource scope accounted for')
