"""Exercise source compiler-server CSharp/VB requests and verify no local fallback."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,shutil,subprocess,sys,time,uuid
build,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir(parents=True)
@lru_cache(maxsize=None)
def native(p):
 s=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',s):return s[1].upper()+':'+s[2:]
 if s.startswith('/clang64/'):return native(Path('/clang64'))+s[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',s],text=True).strip()
tool=out/'toolset λ';shutil.copytree(build/'bin',tool)
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
logs=out/'protocol-logs';logs.mkdir();pipe='codex-source-roslyn53-'+uuid.uuid4().hex
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable',RoslynCommandLineLogFile=native(logs));commands=[]
server_command=[host,native(tool/'VBCSCompiler.dll'),'-pipename:'+pipe]
with (out/'server-stdout.log').open('w') as stream:
 server=subprocess.Popen(server_command,env=env,stdout=stream,stderr=subprocess.STDOUT)
 server_log=None;shutdown=False
 def run(label,args,expected=0):
  r=subprocess.run([host,*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90)
  (out/(label+'.log')).write_text(r.stdout);commands.append(dict(label=label,command=[host,*args],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode,r.stdout)
  return r.stdout
 try:
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   assert server.poll() is None,('server exited',server.returncode)
   matching=[p for p in logs.glob('*.log') if 'Constructing pipe and waiting for connections' in p.read_text(errors='replace')]
   if matching:server_log=matching[0];break
   time.sleep(.25)
  assert server_log is not None,'server did not establish its private pipe'
  for language,compiler,extension,code in [
   ('CSharp','csc','cs','using System; public static class E { extension(string s) { public int TwiceLength => s.Length*2; } } class Program { static int Main() { if ("source".TwiceLength!=12) return 1; Console.WriteLine("PASS server CSharp14"); return 0; } }'),
   ('VisualBasic','vbc','vb','Imports System\nImports System.Linq\nModule Program\n Sub Main()\n Dim q=From n In {1,2,3} Select n*2\n If q.Sum()<>12 Then Throw New Exception("VB query")\n Console.WriteLine("PASS server VisualBasic")\n End Sub\nEnd Module\n')]:
   source=out/(language+' λ.'+extension);source.write_text(code,encoding='utf-8')
   args=['/nostdlib'+('+' if compiler=='csc' else ''),'/target:exe','/debug:portable','/out:"'+native(out/(language+'.dll'))+'"']
   if compiler=='csc':args+=['/langversion:14']
   else:args+=['/nosdkpath','/vbruntime-','/optionstrict+','/optioninfer+','/define:_MYTYPE="Empty"']
   args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(source)+'"']
   rsp=out/(language+' λ.rsp');rsp.write_text('\n'.join(args)+'\n')
   run(language+'-compile',[native(tool/(compiler+'.dll')),'-noconfig','-shared:'+pipe,'-keepalive:30','@'+native(rsp)])
   shutil.copyfile(tool/'csc.runtimeconfig.json',out/(language+'.runtimeconfig.json'))
   assert 'PASS server '+language in run(language+'-execute',[native(out/(language+'.dll'))])
   bad=out/(language+'-bad.'+extension);bad.write_text('class Bad { static void Main() { MissingSymbol(); } }' if compiler=='csc' else 'Module Bad\n Sub Main()\n MissingSymbol()\n End Sub\nEnd Module\n')
   negative=[a for a in args[:-1] if not a.startswith('/out:')]+['/out:"'+native(out/(language+'-bad.dll'))+'"','"'+native(bad)+'"']
   badrsp=out/(language+'-bad.rsp');badrsp.write_text('\n'.join(negative)+'\n')
   expected='CS0103' if compiler=='csc' else 'BC30451'
   assert expected in run(language+'-negative',[native(tool/(compiler+'.dll')),'-noconfig','-shared:'+pipe,'-keepalive:30','@'+native(badrsp)],1)
  client_texts=[p.read_text(errors='replace') for p in logs.glob('*.log') if p!=server_log]
  assert sum('Server compilation completed: Completed' in s for s in client_texts)==4
  assert all('falling back to local build' not in s for s in client_texts)
  server_text=server_log.read_text(errors='replace')
  assert server_text.count(' compiler run')>=8,server_text[-4000:]
  assert server.poll() is None,'owned server must still be running before explicit shutdown'
  run('shutdown',[native(tool/'VBCSCompiler.dll'),'-shutdown','-pipename:'+pipe])
  assert server.wait(timeout=30)==0;shutdown=True
 finally:
  if server.poll() is None:
   try:run('cleanup-shutdown',[native(tool/'VBCSCompiler.dll'),'-shutdown','-pipename:'+pipe])
   except Exception:pass
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=10)
 assert shutdown
record=dict(commands=commands,private_pipe_name=pipe,server_process_id=server.pid,server_exit_code=server.returncode,source_server_sha256=hashlib.sha256((tool/'VBCSCompiler.dll').read_bytes()).hexdigest(),server_protocol_log=server_log.name,completed_server_requests=4,csharp14_and_visualbasic_server_output_executed=True,invalid_source_diagnostics_and_exit1_passed=True,no_local_fallback_verified=True,owned_server_shutdown_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS source NET10 compiler server:4 actual CSharp/VB requests,emitted execution,negative diagnostics,no fallback,owned shutdown')
