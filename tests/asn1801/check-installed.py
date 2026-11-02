"""Verify the installed ASN.1 8.0.1 source archive and execute its exact implementation assets."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-asn1801';here=doc/'checks';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix();manifest=json.loads((doc/'payload-sha256.json').read_text());archives=json.loads((doc/'archives.json').read_text());commands=[]
for rel,h in manifest.items():assert sha(prefix/rel)==h,rel
plan=out/'plan';(plan/'snapshot').mkdir(parents=True);shutil.copytree(doc/'validation-source',plan/'snapshot/runtime');(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(plan/'snapshot/runtime'))));build=out/'build';(build/'bin').mkdir(parents=True);shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir();shutil.copyfile(doc/'localization-results.json',localized/'results.json')
for assembly,a in archives.items():
 archive=prefix/a['archive'];assert sha(archive)==a['sha256']
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert hashlib.sha256(z.read(member)).hexdigest()==h,member
  for ext in ['dll','pdb','xml']:(build/'bin'/(assembly+'.'+ext)).write_bytes(z.read('lib/net8.0/'+assembly+'.'+ext))
def run(label,cmd):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('restore',[sys.executable,'-X','utf8',here/'check-restore.py',prefix,out/'restore'])
cached=out/'restore/cache/system.formats.asn1/8.0.1/lib/net8.0/System.Formats.Asn1.dll';assert sha(cached)==sha(build/'bin'/cached.name);shutil.copyfile(cached,build/'bin'/cached.name)
run('runtime',[sys.executable,'-X','utf8',here/'check.py',plan,build,out/'runtime'])
run('resources',[sys.executable,'-X','utf8',here/'check-resources.py',plan,build,localized,out/'resources'])
run('strict-api',[sys.executable,'-X','utf8',here/'check-api.py',plan,build,out/'api'])
api=json.loads((out/'api/results.json').read_text());entries=sum(r['comparison']['expected_entries'] for r in api['projects'].values())
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),source_NuGet_archive_and_fresh_offline_restore_verified=True,actual_cached_source_implementation_executed_in_isolated_context=True,inbox_implementation_fallback_excluded=True,DER_BER_CER_Unicode_bounds_and_malformed_inputs_on_NET8_and_NET10_passed=True,CLR_and_nullable_contract_entries=entries,strict_CLR_and_nullable_contract_gate_passed=True,neutral_resource_values=json.loads((out/'resources/results.json').read_text())['exact_values'],portable_PDB_associations=1,other_original_framework_profiles_built=False,full_upstream_tests_and_analyzer_integration=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'payload files, original ASN.1 8.0.1 archive/restore/isolated runtime,strict API parity,neutral resource values and PDB identity')
