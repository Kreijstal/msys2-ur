"""Compare every selected original source/resource input with the pinned archive."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
archive,prepared=(Path(p).resolve() for p in sys.argv[1:]);build=json.loads((prepared/'build/results.json').read_text());expected=dict(build['original_selected_cs_sha256']);expected['src/libraries/System.Diagnostics.EventLog/src/Resources/Strings.resx']=build['original_resource_sha256'];expected['src/libraries/System.Diagnostics.EventLog/src/System.Diagnostics.EventLog.csproj']=build['original_project_sha256'];api=json.loads((prepared/'check/api/results.json').read_text());expected['src/libraries/System.Diagnostics.EventLog/ref/System.Diagnostics.EventLog.cs']=api['original_contract_source_sha256'];expected['src/libraries/System.Diagnostics.EventLog/ref/System.Diagnostics.EventLog.netcoreapp.cs']=hashlib.sha256((prepared/'r/src/libraries/System.Diagnostics.EventLog/ref/System.Diagnostics.EventLog.netcoreapp.cs').read_bytes()).hexdigest();plan=json.loads((prepared/'plan/source-inputs.json').read_text());expected['src/libraries/Directory.Build.targets']=plan['original_shared_policy_sha256'];expected['src/libraries/Directory.Build.props']=hashlib.sha256((prepared/'r/src/libraries/Directory.Build.props').read_bytes()).hexdigest();expected['eng/Versions.props']=hashlib.sha256((prepared/'r/eng/Versions.props').read_bytes()).hexdigest();expected['src/libraries/NetCoreAppLibrary.props']=hashlib.sha256((prepared/'r/src/libraries/NetCoreAppLibrary.props').read_bytes()).hexdigest();seen=set();resources=[]
interop=json.loads((prepared/'interop/audit-results.json').read_text())
for project in interop['projects'].values():
 for name,digest in project['original_cs_sha256'].items():
  assert name not in expected or expected[name]==digest
  expected[name]=digest

for n in ['System.Diagnostics.EventLog.Messages.csproj','EventLogMessages.mc','EventLogMessages.rc']:
 p=prepared/'r/src/libraries/System.Diagnostics.EventLog/src/Messages'/n;expected['src/libraries/System.Diagnostics.EventLog/src/Messages/'+n]=hashlib.sha256(p.read_bytes()).hexdigest()
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile():continue
  n=m.name.split('/',1)[-1]
  if n.startswith('src/libraries/System.Diagnostics.EventLog/') and Path(n).suffix in {'.resx','.xlf','.xliff','.resources','.res'}:resources.append(n)
  if n=='src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.res':assert t.extractfile(m).read()==(prepared/'messages/EventLogMessages.res').read_bytes()
  if n in expected:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected);assert set(resources)=={'src/libraries/System.Diagnostics.EventLog/src/Resources/Strings.resx','src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.res'}
package=prepared/'feed/system.diagnostics.eventlog.9.0.11.nupkg'
with zipfile.ZipFile(package) as z:
 assert set(n for n in z.namelist() if n.endswith('.dll'))=={'lib/net9.0/System.Diagnostics.EventLog.dll','runtimes/win/lib/net9.0/System.Diagnostics.EventLog.dll','runtimes/win/lib/net9.0/System.Diagnostics.EventLog.Messages.dll'}
 assert z.read('lib/net9.0/System.Diagnostics.EventLog.xml')==(prepared/'documentation/System.Diagnostics.EventLog.xml').read_bytes()
 for n in ['System.Diagnostics.EventLog.dll','System.Diagnostics.EventLog.pdb']:
  assert z.read('runtimes/win/lib/net9.0/'+n)==(prepared/'build'/n).read_bytes()
  assert z.read('lib/net9.0/'+n)==(prepared/'unsupported-build'/n).read_bytes()
record=dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,original_resource_members=resources,original_resource_scope_complete=True,localized_resource_sources_present=False,source_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),original_production_cs_changes=0,original_target='net9.0',other_original_framework_profiles_built=False,full_dependency_goal_complete=False);(prepared/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('PASS',len(seen),'original source/project/resource bytes;all original resource scope accounted for')

gen=json.loads((prepared/"genfacades/source-inputs.json").read_text());found=set()
with tarfile.open(prepared/"genfacades/arcade-runtime9-6666973b.tar.gz") as t:
 for m in t:
  n=m.name.partition("/")[2]
  if m.isfile() and n in gen["archive_files"]:
   assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==gen["archive_files"][n];found.add(n)
assert found==set(gen["archive_files"])
print("PASS",len(found),"runtime9-pinned Arcade inputs and original message resource regeneration")
