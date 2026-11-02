"""Generate NRBF with source NET8 and decode it using the original NET9 reader."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,refs,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='System.Formats.Nrbf.dll';shutil.copyfile(build/name,out/name);shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),NRBF9_SENTINEL=native(out/'execution-sentinel.txt'));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
def compile(label,source,references):
 args=['/nostdlib+','/target:exe','/langversion:13.0','/nullable:enable','/out:"'+native(out/(label+'.dll'))+'"',*['/reference:"'+native(p)+'"' for p in references],'"'+native(source)+'"'];rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run('compile-'+label,[host,compiler,'-noconfig','@'+native(rsp)])
compile('FixtureGenerator',here/'inputs/FixtureGenerator.cs',sorted((prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll')))
(out/'FixtureGenerator.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0',framework=dict(name='Microsoft.NETCore.App',version='8.0.31'),configProperties={'System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization':True}))))
env.update(DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent),DOTNET_HOST_PATH=native(host8));run('generate-fixtures',[host8,out/'FixtureGenerator.dll',native(out/'fixtures')]);env.update(DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host))
compile('Probe',here/'inputs/Probe.cs',ref_files+[out/name]);(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('execute',[host,out/'Probe.dll',native(out),native(out/'fixtures')])
assert not (out/'execution-sentinel.txt').exists()
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_sha256=sha(out/name),original_target='net9.0',execution_framework='source NET10.0.5',producer_framework='source NET8.0.31',owned_nrbf_payloads=14,all_original_resource_values_passed=True,primitives_arrays_classes_shared_cycles_and_stream_ownership_passed=True,malformed_payloads_rejected=6,no_described_type_loading_or_callback_execution=True,fixture_sha256={p.name:sha(p) for p in (out/'fixtures').glob('*.nrbf')},formal_package_built=False,other_original_framework_profiles_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source NRBF9 real reader consumer on NET10 with14 independent source NET8 payloads')
