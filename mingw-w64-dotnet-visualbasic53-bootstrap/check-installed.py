"""Validate a staged/installed VB companion together with owned source CSharp."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
doc=prefix/'share/doc/dotnet-visualbasic53-bootstrap';relative=Path('lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap')
manifest=json.loads((doc/'payload-files.json').read_text())
for n,d in manifest.items():assert hashlib.sha256((prefix/n).read_bytes()).hexdigest()==d,n
installed=Path('/clang64');csharp=json.loads((installed/'share/doc/dotnet-csharp-compiler53-bootstrap/payload-files.json').read_text())
for n,d in csharp.items():assert hashlib.sha256((installed/n).read_bytes()).hexdigest()==d,n
assert not set(manifest)&set(csharp),'Companion packages must own disjoint files'
build=out/'merged toolset λ';binary=build/'bin';shutil.copytree(installed/relative,binary,ignore=shutil.ignore_patterns('Microsoft.CodeAnalysis.VisualBasic*','vbc*','VBCSCompiler*'))
shutil.copytree(prefix/relative,binary,dirs_exist_ok=True)
for n in ['VBChecks.dll','VBChecks.pdb','VBChecks.runtimeconfig.json']:shutil.copyfile(doc/'checks'/n,binary/n)
for n in ['localization.json','api-vb.txt','friends.json']:shutil.copyfile(doc/'checks'/n,out/n)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(installed/'lib/dotnet10'),DOTNET_ROOT_X64=native(installed/'lib/dotnet10'),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable');commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('vb-api-resource',[host,native(binary/'VBChecks.dll'),native(out/'localization.json'),native(installed/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0'),native(out/'api-vb.txt'),native(out/'friends.json'),native(doc/'checks/embedded-templates')])
for script,label in [('check-net10-vbc.py','vbc-check'),('check-net10-server.py','server-check')]:run(label,['/usr/bin/python3',str(doc/'checks'/script),str(build),str(out/label)])
(out/'results.json').write_text(json.dumps(dict(commands=commands,installed_vb_payload_files_verified=len(manifest),installed_csharp_payload_files_verified=len(csharp),package_file_ownership_disjoint=True,all_original_vb_api_resources_and_templates_verified=True,real_vbc_compilation_and_execution_verified=True,real_server_requests_and_no_fallback_and_owned_shutdown_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(manifest),'VB/server files;',len(csharp),'CSharp dependency files;full VB and real client/server suites')
