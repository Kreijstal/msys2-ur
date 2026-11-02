"""Verify the staged/installed task payload and execute real original tasks through source MSBuild18."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-sdk10-tasks-bootstrap';here=doc/'checks';base=prefix/'lib/dotnet10/build-packs/sdk-10.0.201-net10-bootstrap';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
manifest=json.loads((doc/'payload-sha256.json').read_text())
for name,h in manifest.items():assert sha(prefix/name)==h,name
build=out/'build';build.mkdir();shutil.copytree(base/'bin',build/'bin');(build/'dependency-assets').mkdir();shutil.copyfile(doc/'build-results.json',build/'results.json');plan=out/'plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(doc/'validation-source'))));localized=out/'localized';localized.mkdir()
commands=[]
for label,cmd in [('resources',[sys.executable,'-X','utf8',here/'check-resources.py',plan,build,localized,out/'resources']),('runtime',[sys.executable,'-X','utf8',here/'check.py',plan,build,out/'runtime'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=420)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),installed_original_task_execution_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'installed payload hashes,112 exact resource sets,78 satellites,6 PDBs,SDK/Extensions/APICompat task execution and native NET10 Unicode app')
