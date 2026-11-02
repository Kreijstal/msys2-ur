"""Verify installed VB shell options, MSYS paths and actual emitted execution."""
from pathlib import Path
import json,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
launcher=prefix/'bin/vbc53-bootstrap';commands=[]
def run(label,args):
 r=subprocess.run([str(launcher),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/(label+'.log')).write_text(r.stdout);commands.append(dict(label=label,command=[str(launcher),*args],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode,r.stdout)
 return r.stdout
assert run('dash-version',['-version']).startswith('5.3.')
assert run('slash-version',['/version']).startswith('5.3.')
source=out/'source λ.vb';source.write_text('Imports System\nImports System.Linq\nModule Program\n Sub Main()\n Dim q=From n In {1,2,3} Select n*2\n If q.Sum()<>12 Then Throw New Exception("Query result")\n Console.WriteLine("PASS installed VB shell launcher:slash flags,Unicode MSYS paths,emitted LINQ execution")\n End Sub\nEnd Module\n',encoding='utf-8')
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
rsp=out/'response λ.rsp';rsp.write_text('\n'.join(['/nostdlib','/nosdkpath','/vbruntime-','/target:exe','/optionstrict+','/optioninfer+','/define:_MYTYPE="Empty"','/out:"'+native(out/'probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in refs]])+'\n')
run('compile',['/noconfig','@'+str(rsp),str(source)])
(out/'probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
command=[str(prefix/'lib/dotnet10/dotnet.exe'),native(out/'probe.dll')];r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'execute.log').write_text(r.stdout);commands.append(dict(label='execute',command=command,exit_code=r.returncode));assert r.returncode==0 and 'PASS installed VB shell launcher' in r.stdout
(out/'results.json').write_text(json.dumps(dict(commands=commands,slash_and_dash_options_passed=True,unicode_msys_source_and_response_paths_passed=True,emitted_net10_vb_linq_execution_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS installed VB shell launcher:dash/slash options,Unicode MSYS source/response paths,NET10 query execution')
