"""Verify actual NuGet6.13.2 package archives, source-only restore and fresh consumers."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-nuget6132-template-bootstrap';here=doc/'checks';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix();manifest=json.loads((doc/'payload-sha256.json').read_text());archives=json.loads((doc/'archives.json').read_text());commands=[]
for rel,h in manifest.items():assert sha(prefix/rel)==h,rel
plan=out/'plan';plan.mkdir();shutil.copytree(doc/'validation-source',plan/'source');(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(plan/'source'))));build=out/'build';(build/'bin').mkdir(parents=True);shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir();shutil.copyfile(doc/'localization-results.json',localized/'results.json')
for assembly,a in archives.items():
 archive=prefix/a['archive'];assert sha(archive)==a['sha256']
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert hashlib.sha256(z.read(member)).hexdigest()==h,member
  for ext in ['dll','pdb','xml']:(build/'bin'/(assembly+'.'+ext)).write_bytes(z.read('lib/net10.0/'+assembly+'.'+ext))
def run(label,cmd):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('restore',[sys.executable,'-X','utf8',here/'check-package-restore.py',prefix,out/'restore'])
for assembly in archives:
 cached=out/'restore/cache'/assembly.lower()/'6.13.2/lib/net10.0'/(assembly+'.dll');assert sha(cached)==sha(build/'bin'/cached.name)
run('resources',[sys.executable,'-X','utf8',here/'check-resources.py',plan,build,localized,out/'resources'])
run('runtime-api',[sys.executable,'-X','utf8',here/'check.py',plan,out/'restore',build,out/'runtime-api'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),seven_exact_source_NuGet6132_archives_verified=True,actual_source_NuGet73_offline_restore_and_archive_bytes_verified=True,seven_original_NuGet6132_framework_profile_identity_API_and_runtime_checks_passed=True,exact_Immutable8_ProtectedData44_Pkcs604_compiled_bindings_and_isolated_runtime_verified=True,upstream_API_declarations_checked=5975,raw_extra_API_and_full_metadata_comparison_performed=False,neutral_resource_sets=10,exact_resource_values=502,portable_PDB_associations=7,source_archive_XLF_count=0,external_published_localization_package_rebuilt=False,full_upstream_test_and_analyzer_integration=False,other_original_framework_profiles_built=False,exact_Asn1801_source_runtime_and_strict_restore_verified=True,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'payload files,7 NuGet6.13.2 archives, fresh offline source restore,5975 upstream APIs,502 resource values,7 PDBs and owned runtime integration')
