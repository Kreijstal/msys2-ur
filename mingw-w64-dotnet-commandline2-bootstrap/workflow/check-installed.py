"""Validate both actual archive profiles and source .NET8/10 runtime consumers."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,xml.etree.ElementTree as E,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-commandline2-bootstrap';manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
build=out/'build';build.mkdir();records=json.loads((doc/'build-results.json').read_text());shutil.copyfile(doc/'build-results.json',build/'results.json');translations=json.loads((doc/'localization-results.json').read_text())
with zipfile.ZipFile(prefix/'lib/dotnet/library-packs/system.commandline.2.0.2.nupkg') as z:
 meta=E.fromstring(z.read('System.CommandLine.nuspec'));assert meta.findtext('./metadata/version')=='2.0.2';assert len(meta.findall('./metadata/dependencies/group'))==2;assert meta.find('./metadata/dependencies/group[@targetFramework="netstandard2.0"]/dependency').get('version')=='[4.5.5]';assert not any(n.endswith('/System.Memory.dll') or n.endswith('/System.Runtime.CompilerServices.Unsafe.dll') for n in z.namelist())
 for tfm in ['net10.0','netstandard2.0']:
  for member in z.namelist():
   if member.startswith('lib/'+tfm+'/'):
    dest=build/tfm/'bin'/member.removeprefix('lib/'+tfm+'/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(member))
 for r in records['projects']:
  for ext,h in r['output_sha256'].items():assert hashlib.sha256((build/r['original_target']/'bin'/('System.CommandLine.'+ext)).read_bytes()).hexdigest()==h
 for rel,h in translations['satellite_sha256'].items():assert hashlib.sha256((build/rel).read_bytes()).hexdigest()==h
plan=out/'plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=(doc/'validation-source').as_posix())));local=out/'localized';local.mkdir();shutil.copyfile(doc/'expected-localization.json',local/'expected.json');cmd=[sys.executable,'-X','utf8',doc/'checks/check.py',plan,build,local,out/'consumer']
with (out/'consumer.log').open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
assert r.returncode==0,r.returncode
restore=[sys.executable,'-X','utf8',doc/'checks/check-restore.py',prefix,out/'feed-restore']
with (out/'feed-restore.log').open('w',encoding='utf-8') as f:rr=subprocess.run(restore,stdout=f,stderr=subprocess.STDOUT,timeout=240)
assert rr.returncode==0,rr.returncode
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd],exit_code=0,payload_files_verified=len(manifest),both_original_archive_profiles_verified=True,actual_source_NuGet73_NET10_archive_restore_passed=True,original_cultures=14,archive_satellites=28,source_runtime_executions=3,unchanged_upstream_tokenization_cases_per_execution=9,NS2_reference_only_dependencies_runtime_substituted=False,original_NS2_memory_package_runtime_closure_verified=False,full_original_trim_analyzer_integration=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'consumer.log').read_text(encoding='utf-8'));print('PASS',len(manifest),'installed payload hashes and both exact source archive profiles')
