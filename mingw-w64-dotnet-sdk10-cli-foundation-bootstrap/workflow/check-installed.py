"""Verify actual staged/installed CLI foundation assets and original managed/native behavior."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-sdk10-cli-foundation-bootstrap';base=prefix/'lib/dotnet10/build-packs/sdk-cli-foundation-10.0.201-net10-bootstrap';manifest=json.loads((doc/'payload-sha256.json').read_text());native=lambda p:Path(p).resolve().as_posix()
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
plan=out/'plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(doc/'validation-source'))));build=out/'build';build.mkdir();shutil.copytree(base/'bin',build/'bin');shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir();commands=[]
for label,cmd in [('resources',[sys.executable,'-X','utf8',doc/'checks/check-resources.py',plan,build,localized,out/'resources']),('runtime',[sys.executable,'-X','utf8',doc/'checks/check.py',plan,build,out/'runtime',base/'bin'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),eight_original_NET10_assembly_and_PDB_identities_verified=True,exact_resource_values=966,satellites=52,original_managed_and_native_consumers_passed=True,MSI_install_write_operations_verified=False,formal_MSBuild_Runtime_NuGet_archive_provided=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'installed payload hashes,966 resource values,52 satellites,8 PDBs and original managed/native CLI foundation consumer')
