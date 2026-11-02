"""Run original source NET10 vbc, emit a real VB application and check errors."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
host='/clang64/lib/dotnet10/dotnet.exe';tool=build/'bin/vbc.dll'
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable');commands=[]
def run(label,args,expected=0):
 r=subprocess.run([host,*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/(label+'.log')).write_text(r.stdout);commands.append(dict(label=label,command=[host,*args],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode,r.stdout)
 return r.stdout
assert run('version',[native(tool),'-noconfig','-version']).startswith('5.3.')
source=out/'VB compiler λ.vb';source.write_text('''Imports System
Imports System.Linq
Imports System.Threading.Tasks
Module VBProbe
 Async Function Answer() As Task(Of Integer)
  Await Task.Yield()
  Dim values = From n In {1, 2, 3} Select n * 2
  Return values.Sum()
 End Function
 Sub Main()
  If Environment.Version.Major <> 10 OrElse Answer().GetAwaiter().GetResult() <> 12 Then
   Environment.ExitCode = 1
   Return
  End If
  Console.WriteLine("PASS source NET10 vbc: VB LINQ, async/await and emitted program execution λ")
 End Sub
End Module
''',encoding='utf-8')
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib','/nosdkpath','/vbruntime-','/target:exe','/langversion:latest','/optionstrict+','/optioninfer+','/define:_MYTYPE="Empty"','/debug:portable','/out:"'+native(out/'probe.dll')+'"']
args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(source)+'"']
rsp=out/'compile λ.rsp';rsp.write_text('\n'.join(args)+'\n');run('compile',[native(tool),'-noconfig','@'+native(rsp)])
shutil.copyfile(build/'bin/vbc.runtimeconfig.json',out/'probe.runtimeconfig.json')
assert 'PASS source NET10 vbc' in run('execute',[native(out/'probe.dll')])
bad=out/'bad.vb';bad.write_text('Module Bad\n Sub Main()\n MissingSymbol()\n End Sub\nEnd Module\n')
negative=[a for a in args[:-1] if not a.startswith('/out:')]+['/out:"'+native(out/'bad.dll')+'"','"'+native(bad)+'"']
rsp2=out/'negative.rsp';rsp2.write_text('\n'.join(negative)+'\n')
assert 'BC30451' in run('negative',[native(tool),'-noconfig','@'+native(rsp2)],1)
assert not (out/'bad.dll').exists()
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_compiler_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),source_visualbasic_library_sha256=hashlib.sha256((build/'bin/Microsoft.CodeAnalysis.VisualBasic.dll').read_bytes()).hexdigest(),real_net10_vbc_execution_passed=True,emitted_vb_linq_async_program_execution_passed=True,unicode_response_file_passed=True,invalid_source_exit_code=1,all_visualbasic_api_resources_verified=False,compiler_server_execution_verified=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS source NET10 vbc:version,Unicode response file,LINQ/async VB execution and expected BC30451 exit1')
