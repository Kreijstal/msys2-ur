"""Execute isolated cross-architecture metadata inspection without fixture execution."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,refs,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='System.Reflection.MetadataLoadContext.dll';shutil.copyfile(build/name,out/name);shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
def compile(label,source,platform,extras=[]):
 args=['/nostdlib+','/target:'+('exe' if label=='Probe' else 'library'),'/langversion:preview','/nullable:enable','/platform:'+platform,'/out:"'+native(out/(label+'.dll'))+'"',*['/reference:"'+native(p)+'"' for p in ref_files+extras],'"'+native(source)+'"'];rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run('compile-'+label,[host,compiler,'-noconfig','@'+native(rsp)])
compile('FixtureAny',here/'inputs/Fixture.cs','anycpu');compile('FixtureX86',here/'inputs/Fixture.cs','x86');compile('Probe',here/'inputs/Probe.cs','anycpu',[out/name])
(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('execute',[host,out/'Probe.dll',native(out),native(refs)])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_sha256=sha(out/name),original_target='net9.0',execution_framework='source NET10.0.5',cross_architecture_unicode_generic_attribute_metadata_passed=True,metadata_method_and_attribute_execution_rejected=True,no_fixture_runtime_loading_or_module_initializer_execution=True,invalid_pe_missing_assembly_and_context_disposal_passed=True,neutral_resource_strings=len(json.loads((out/'neutral-strings.json').read_text())),formal_package_built=False,other_original_framework_profiles_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source NET9 MetadataLoadContext real metadata/isolation/lifetime consumer on NET10')
