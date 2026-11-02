"""Run NET10 source restore against actual candidate/installed source archives."""
from pathlib import Path
import json,os,shutil,subprocess,sys
consumer,candidate,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();binary=out/'bin';shutil.copytree(consumer,binary)
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/out:"'+native(binary/'PackagedRestore.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+list(binary.glob('*.dll')) if p.name!='Check.dll']+['"'+native(here/'PackagedRestore.cs')+'"']
(out/'compile.rsp').write_text('\n'.join(args)+'\n');shutil.copyfile(binary/'Check.runtimeconfig.json',binary/'PackagedRestore.runtimeconfig.json')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),NUGET_SCRATCH=native(out/'scratch'),NUGET_HTTP_CACHE_PATH=native(out/'http-cache'),NUGET_PLUGINS_CACHE_PATH=native(out/'plugins-cache'));commands=[]
for label,cmd in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(out/'compile.rsp')]),('execute',[host,binary/'PackagedRestore.dll',out/'owned-work',candidate/'lib/dotnet/library-packs',prefix/'lib/dotnet/library-packs'])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,actual_eight_source_packages_restored=True,full_sdk10_built=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))
