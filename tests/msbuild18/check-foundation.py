"""Compile and execute a source NET10 consumer of StringTools and Framework."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
strings,framework,out=(Path(p).resolve() for p in sys.argv[1:4]);assert not out.exists();out.mkdir()
here=Path(__file__).resolve().parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
for root,name in [(strings,'Microsoft.NET.StringTools'),(framework,'Microsoft.Build.Framework')]:shutil.copyfile(root/(name+'.dll'),out/(name+'.dll'))
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
refs+=[out/'Microsoft.NET.StringTools.dll',out/'Microsoft.Build.Framework.dll']
args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:enable','/debug:portable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in refs],'"'+native(here/'FoundationProbe.cs')+'"']
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_HOST_PATH=native(Path(host)))
(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
commands=[]
for label,command in [('compile',[host,native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll')),'-noconfig','@'+native(rsp)]),('execute',[host,native(out/'Probe.dll')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('Microsoft*.dll')},real_net10_stringtools_and_framework_consumer_passed=True,concurrent_interning_operations=20000,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS source NET10 StringTools/Framework executed consumer,20000 interning operations and task/event callbacks')
