"""Check installed or staged compiler bytes and its full NET10 API consumer."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
doc=prefix/'share/doc/dotnet-csharp-compiler53-bootstrap';tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
manifest=json.loads((doc/'payload-files.json').read_text())
for n,d in manifest.items():assert hashlib.sha256((prefix/n).read_bytes()).hexdigest()==d,n
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
runtime=Path('/clang64/lib/dotnet10');host=runtime/'dotnet.exe'
env=dict(os.environ,DOTNET_ROOT=native(runtime),DOTNET_ROOT_X64=native(runtime),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable')
commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('version',[str(host),native(tool/'csc.dll'),'-noconfig','-version'])
assert (out/'version.log').read_text().startswith('5.3.')
app=out/'installed compiler checks λ';shutil.copytree(tool,app)
assets=['api-common.txt','api-csharp.txt','localization-common.json','localization-csharp.json','original-localization-coverage.json']
for n in ['Check.dll','Check.pdb','Check.runtimeconfig.json',*assets]:shutil.copyfile(doc/'checks'/n,app/n)
run('api-resource-compiler',[str(host),native(app/'Check.dll'),native(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')),*[native(app/n) for n in assets]])
(out/'results.json').write_text(json.dumps(dict(commands=commands,installed_manifested_bytes_verified=len(manifest),exact_installed_tool_and_satellite_bytes_verified=True,all_original_api_resource_compiler_checks_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(manifest),'installed source compiler bytes; real NET10 version/API/resource/compiler suite')
