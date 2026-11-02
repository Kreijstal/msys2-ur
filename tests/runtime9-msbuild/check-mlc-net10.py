"""Exercise a real SDK10-style NET10 compiler metadata inspection case."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
library,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(library,out/library.name);refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0').glob('*.dll'));assert len(refs)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in refs+[out/library.name]],'"'+native(here/'MetadataNet10Probe.cs')+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
for label,command in [('compile',[host,compiler/'csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,out/'Probe.dll',native(compiler)])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,library_sha256=sha(library),inspected_compiler_sha256={n:sha(compiler/n) for n in ['Microsoft.CodeAnalysis.CSharp.dll','csc.dll']},real_net10_compiler_metadata_inspection_passed=True,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS real source NET10 compiler metadata inspection with source NET9 library')
