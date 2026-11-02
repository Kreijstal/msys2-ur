"""Rebuild only the NET10 VB consumer when adjusting validation fixtures."""
from pathlib import Path
import json,os,subprocess,sys
source,out=(Path(p).resolve() for p in sys.argv[1:3]);here=Path(__file__).resolve().parent;binary=out/'bin'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
files=sorted((here/'vb-check-inputs').glob('*.cs'));assert len(files)==3
args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:enable','/deterministic+','/debug:portable','/out:"'+native(binary/'VBChecks.dll')+'"']
args+=['/reference:"'+native(p)+'"' for p in refs+[binary/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.VisualBasic']]]+['"'+native(p)+'"' for p in files]
rsp=out/'consumer.rsp';rsp.write_text('\n'.join(args)+'\n')
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable');commands=[]
for label,command in [('consumer',[host,native(binary/'csc.dll'),'-noconfig','@'+native(rsp)]),('consumer-run',[host,native(binary/'VBChecks.dll'),native(out/'localization.json'),native(refs[0].parent),native(out/'api-vb.txt'),native(out/'friends.json'),native(source/'src/Compilers/VisualBasic/Portable/Symbols/EmbeddedSymbols')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'consumer-results.json').write_text(json.dumps(dict(commands=commands,all_original_vb_api_resource_and_behavior_checks_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS NET10 VB API/resource/behavior/friend/template suite')
