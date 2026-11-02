"""Execute the original binding generator against original NET10 configuration libraries."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';native=lambda p:Path(p).resolve().as_posix();binary=out/'bin';binary.mkdir();generated=out/'generated';generated.mkdir();commands=[]
records=json.loads((build/'results.json').read_text())['projects']
for r in records:
 if r['original_framework']=='net10.0':shutil.copyfile(build/'bin'/(r['assembly']+'.dll'),binary/(r['assembly']+'.dll'))
for p in (build/'dependency-assets').glob('Microsoft.Extensions.*.dll'):
 if not p.stem.endswith('.SourceGeneration'):shutil.copyfile(p,binary/p.name)
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/nullable:enable','/langversion:preview','/features:InterceptorsNamespaces=Microsoft.Extensions.Configuration.Binder.SourceGeneration','/out:"'+native(binary/'Check.dll')+'"','/generatedfilesout:"'+native(generated)+'"','/analyzer:"'+native(build/'bin/Microsoft.Extensions.Options.SourceGeneration.dll')+'"']+['/reference:"'+native(p)+'"' for p in [*refs,*binary.glob('*.dll')]]+['"'+native(here/'Check.cs')+'"']
(out/'compile.rsp').write_text('\n'.join(args)+'\n');(binary/'Check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net10.0','framework':{'name':'Microsoft.NETCore.App','version':'10.0.5'}}}));env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent))
for label,cmd in [('compile',[host,compiler,'-noconfig','@'+native(out/'compile.rsp')]),('execute',[host,binary/'Check.dll'])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
assert list(generated.rglob('*.cs'))
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_NET10_libraries_executed=True,original_NS2_Roslyn44_Options_generator_executed=True,DI_options_reload_JSON_logging_and_native_Console_passed=True,generated_source_sha256={p.relative_to(generated).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in generated.rglob('*.cs')},formal_packages_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))
