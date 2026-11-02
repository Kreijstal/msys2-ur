"""Run with native Windows Python: prove installed clients create and share their server."""
from pathlib import Path
import ctypes,json,os,re,subprocess,sys,uuid
prefix,out=(Path(p).resolve() for p in sys.argv[1:3]);mode=sys.argv[3] if len(sys.argv)==4 else '--raw'
assert mode in {'--raw','--cmd','--shell'}
assert not out.exists();out.mkdir(parents=True)
tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';host=prefix/'lib/dotnet10/dotnet.exe';logs=out/'protocol-logs';logs.mkdir()
env=dict(os.environ,DOTNET_ROOT=str(host.parent),DOTNET_ROOT_X64=str(host.parent),DOTNET_HOST_PATH=str(host),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable',RoslynCommandLineLogFile=str(logs));pipe='codex-roslyn53-auto-'+uuid.uuid4().hex;commands=[]
if mode!='--raw':env['DOTNET_HOST_PATH']=str(prefix/'lib/dotnet/dotnet.exe')
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.WaitForSingleObject.restype=ctypes.c_ulong
kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
process_handle=None;pid=None;shutdown=False
def run(label,args):
 if label.endswith('-compile') and mode=='--cmd':
  compiler=Path(args[0]).stem
  batch='"'+str(tool/(compiler+'53.cmd'))+'" '+subprocess.list2cmdline(args[1:])
  command=subprocess.list2cmdline([os.environ.get('COMSPEC','cmd.exe')])+' /d /s /c "'+batch+'"'
 elif label.endswith('-compile') and mode=='--shell':
  compiler=Path(args[0]).stem
  command=[str(prefix.parent/'usr/bin/bash.exe'),str(prefix/'bin'/(compiler+'53-bootstrap')),*args[1:]]
 else:command=[str(host),*args]
 r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=60)
 (out/(label+'.log')).write_text(r.stdout,encoding='utf-8');commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode,r.stdout)
try:
 for compiler,extension,code in [('csc','cs','public class AutoCS { public static int Value => 42; }'),('vbc','vb','Public Module AutoVB\n Public Function Value() As Integer\n Return 42\n End Function\nEnd Module\n')]:
  source=out/(compiler+' λ.'+extension);source.write_text(code,encoding='utf-8')
  args=['/nostdlib'+('+' if compiler=='csc' else ''),'/utf8output','/target:library','/out:"'+str(out/(compiler+'.dll'))+'"']
  if compiler=='vbc':args+=['/nosdkpath','/vbruntime-','/define:_MYTYPE="Empty"']
  args+=['/reference:"'+str(p)+'"' for p in refs]+['"'+str(source)+'"']
  rsp=out/(compiler+' λ.rsp');rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
  run(compiler+'-compile',[str(tool/(compiler+'.dll')),'-noconfig','-shared:'+pipe,'-keepalive:30','@'+str(rsp)])
  assert (out/(compiler+'.dll')).is_file()
  texts=[p.read_text(encoding='utf-8',errors='replace') for p in logs.glob('*.log')]
  assert all('falling back to local build' not in s for s in texts),'client fell back to local compilation'
  creates=[int(n) for s in texts for n in re.findall(r'Successfully created process with process id (\d+)',s)]
  assert len(set(creates))==1,creates
  if process_handle is None:
   pid=creates[0];process_handle=kernel.OpenProcess(0x00101000,False,pid);assert process_handle,ctypes.get_last_error()
   size=ctypes.c_ulong(32768);image=ctypes.create_unicode_buffer(size.value)
   assert kernel.QueryFullProcessImageNameW(process_handle,0,image,ctypes.byref(size)),ctypes.get_last_error()
   assert Path(image.value).resolve()==host.resolve(),image.value
  assert kernel.WaitForSingleObject(process_handle,0)==258,'owned auto-started server exited early'
 texts=[p.read_text(encoding='utf-8',errors='replace') for p in logs.glob('*.log')]
 assert sum(s.count('Server compilation completed: Completed') for s in texts)==2
 assert all('falling back to local build' not in s for s in texts)
 run('shutdown',[str(tool/'VBCSCompiler.dll'),'-shutdown','-pipename:'+pipe])
 assert kernel.WaitForSingleObject(process_handle,30000)==0;shutdown=True
finally:
 if not shutdown:
  try:run('cleanup-shutdown',[str(tool/'VBCSCompiler.dll'),'-shutdown','-pipename:'+pipe])
  except Exception:pass
  if process_handle:assert kernel.WaitForSingleObject(process_handle,45000)==0,'owned server did not shut down'
 if process_handle:kernel.CloseHandle(process_handle)
(out/'results.json').write_text(json.dumps(dict(commands=commands,invocation_mode=mode,incorrect_inherited_sdk8_host_overridden=mode!='--raw',owned_server_process_id=pid,server_image_path_verified=True,clients_automatically_started_and_shared_exactly_one_server=True,completed_server_requests=2,no_local_fallback_verified=True,owned_server_shutdown_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS installed clients auto-start and share one source NET10 server;Windows process identity,no fallback and shutdown verified')
