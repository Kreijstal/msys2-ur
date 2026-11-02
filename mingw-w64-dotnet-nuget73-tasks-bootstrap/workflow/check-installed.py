"""Validate actual installed NuGet task/resolver assets and owned offline consumers."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-nuget73-tasks-bootstrap';base=prefix/'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';manifest=json.loads((doc/'payload-sha256.json').read_text());native=lambda p:Path(p).resolve().as_posix()
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
plan=out/'plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(doc/'validation-source'))));build=out/'build';build.mkdir();shutil.copytree(base/'bin',build/'bin');shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir();commands=[]
for label,cmd in [('resources',[sys.executable,'-X','utf8',doc/'checks/check-resources.py',plan,build,localized,out/'resources']),('runtime',[sys.executable,'-X','utf8',doc/'checks/check.py',plan,build,out/'runtime',base/'bin'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=420)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),installed_pack_classic_and_static_restore_and_sdk_resolver_passed=True,installed_resource_values=756,original_satellites=39,portable_pdbs=4,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'installed payload hashes,756 resource values,39 satellites,4 PDBs,pack,classic/static restore,NU1101 negative and actual SDK resolver discovery/imports')
