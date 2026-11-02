"""Check both option syntaxes and MSYS source/response paths of the shell launcher."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
command=prefix/'bin/csc53-bootstrap';native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();commands=[]
def run(label,args,expected=0):
 r=subprocess.run([str(command),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/(label+'.log')).write_text(r.stdout);commands.append(dict(label=label,command=[str(command),*args],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode,r.stdout)
 return r.stdout
for arg,label in [('-version','dash-version'),('/version','slash-version')]:assert run(label,[arg]).startswith('5.3.')
source=out/'source λ.cs';source.write_text('''using System;
public static class Extensions { extension(string text) { public int TwiceLength => text.Length*2; } }
class Program { static int Main() { if ("source".TwiceLength != 12) return 1; Console.WriteLine("PASS installed shell launcher:slash flags,MSYS source/response paths,CSharp14 NET10 execution"); return 0; } }
''',encoding='utf-8')
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
rsp=out/'response λ.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/langversion:14','/out:"'+native(out/'probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in refs]])+'\n')
run('compile',['/noconfig','@'+str(rsp),str(source)])
(out/'probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
r=subprocess.run([str(prefix/'lib/dotnet10/dotnet.exe'),native(out/'probe.dll')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'execute.log').write_text(r.stdout);assert r.returncode==0 and 'PASS installed shell launcher' in r.stdout,(r.returncode,r.stdout)
(out/'results.json').write_text(json.dumps(dict(commands=commands,managed_execution_exit_code=r.returncode,installed_launcher_sha256=hashlib.sha256(command.read_bytes()).hexdigest(),slash_and_dash_options_passed=True,msys_unicode_source_and_response_paths_passed=True,csharp14_execution_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS installed shell launcher:dash/slash options,Unicode MSYS response/source paths,CSharp14 NET10 execution')
