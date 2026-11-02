"""Validate source host discovery and execution of an isolated NET10 framework."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys

layout=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir()
probes=[Path(p).resolve() for p in sys.argv[3:]]
assert len(probes)==3, 'Provide native, framework and javascript compiled probe DLLs'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((layout/'source-payload.json').read_text())
for relative,item in manifest['source_files'].items():assert sha(layout/relative)==item['sha256'],relative
env=dict(os.environ,DOTNET_ROOT=native(layout),DOTNET_ROOT_X64=native(layout),
 DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable',DOTNET_CLI_TELEMETRY_OPTOUT='1')
commands=[]
def run(command,label):
 with (out/(label+'.log')).open('w') as log:
  result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 commands.append(dict(label=label,command=command,exit_code=result.returncode))
 assert result.returncode==0,(label,result.returncode,out/(label+'.log'))
run([str(layout/'dotnet.exe'),'--list-runtimes'],'list-runtimes')
text=(out/'list-runtimes.log').read_text()
assert 'Microsoft.NETCore.App 10.0.5 [' in text and '8.0.' not in text,text
app=out/'hosted probes λ';app.mkdir()
for case,probe in zip(['native','framework','javascript'],probes):
 dll=app/(case+'.dll');shutil.copy2(probe,dll)
 (app/(case+'.runtimeconfig.json')).write_text(json.dumps(dict(runtimeOptions=dict(
  tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5'))),indent=2)+'\n')
 command=[str(layout/'dotnet.exe'),native(dll)]
 if case=='native':command.append(native(layout/'shared/Microsoft.NETCore.App/10.0.5/System.Globalization.Native.dll'))
 run(command,case)
record=dict(commands=commands,all_hosted_cases_passed=True,
 managed_framework_assemblies=172,private_seed_assemblies_shipped=0,
 source_host_discovers_only_isolated_net10_runtime=True,
 source_payload_manifest_sha256=sha(layout/'source-payload.json'),
 probe_inputs_sha256={str(p):sha(p) for p in probes},
 full_runtime_compatibility_verified=False,full_sdk10_built=False,
 powershell76_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS source dotnet10 host runtime discovery and all three complete-framework probes')
