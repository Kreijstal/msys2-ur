"""Compare all available public framework outputs to their original NET10 contracts."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
plan=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap');dotnet='/clang64/lib/dotnet/dotnet.exe';refs=Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')
for name in ['Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']:shutil.copy2(compiler/name,out/name)
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'FrameworkApi.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs.glob('*.dll') if p.name not in {'System.Collections.Immutable.dll','System.Reflection.Metadata.dll'}]+['/reference:"'+native(out/name)+'"' for name in ['Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]+['"'+native(here/'inputs/FrameworkApi.cs')+'"']
(out/'compile.rsp').write_text('\n'.join(args)+'\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
with (out/'build.log').open('w') as f:r=subprocess.run([dotnet,native(compiler/'CompilerHost.dll'),'-noconfig','@'+native(out/'compile.rsp')],env=env,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'build.log')
deps=json.loads((compiler/'CompilerHost.deps.json').read_text());target=deps['targets'][deps['runtimeTarget']['name']];app=target.pop('CompilerHost/1.0.0');app['runtime']={'FrameworkApi.dll':{}};target['FrameworkApi/1.0.0']=app;deps['libraries']['FrameworkApi/1.0.0']=deps['libraries'].pop('CompilerHost/1.0.0')
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:
 app['dependencies'][name]='5.0.0';target[name+'/5.0.0']={'runtime':{name+'.dll':{'assemblyVersion':'5.0.0.0','fileVersion':'5.0.0.0'}}};deps['libraries'][name+'/5.0.0']={'type':'project','serviceable':False,'sha512':''}
(out/'FrameworkApi.deps.json').write_text(json.dumps(deps,indent=2)+'\n');shutil.copy2(compiler/'CompilerHost.runtimeconfig.json',out/'FrameworkApi.runtimeconfig.json')
command=[dotnet,native(out/'FrameworkApi.dll'),native(plan),native(out/'results.json'),native(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')),native(Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5/System.Private.CoreLib.dll'))]
with (out/'compare.log').open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
(out/'compare.exit').write_text(str(r.returncode)+'\n');(out/'tool-inputs.json').write_text(json.dumps({p.name:sha(p) for p in out.glob('*.dll')},indent=2)+'\n')
assert r.returncode==0,(r.returncode,out/'compare.log',out/'results.json')
print('PASS current original framework contract metadata API comparison')
