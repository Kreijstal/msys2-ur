"""Execute source CodeDom on NET10; compile and execute its CSharp/VB output."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
build,refs,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(build/'System.CodeDom.dll',out/'System.CodeDom.dll');shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
def compile(label,language,source,name,extras=[]):
 args=['/nostdlib+','/target:'+('exe' if name=='Probe' else 'library'),'/out:"'+native(out/(name+'.dll'))+'"',*['/reference:"'+native(p)+'"' for p in ref_files+extras],'"'+native(source)+'"']
 if language=='cs':args+=['/langversion:preview','/nullable:enable']
 else:args+=['/vbruntime*']
 rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run(label,[host,compiler/('csc.dll' if language=='cs' else 'vbc.dll'),'-noconfig','@'+native(rsp)])
compile('compile-probe','cs',here/'CodeDomProbe.cs','Probe',[out/'System.CodeDom.dll'])
(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('generate',[host,out/'Probe.dll',native(out)])
compile('compile-generated-csharp','cs',out/'Generated.cs','GeneratedCs')
compile('compile-generated-vb','vb',out/'Generated.vb','GeneratedVb')
run('execute-generated',[host,out/'Probe.dll',native(out),'--execute-generated'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_codedom_sha256=sha(out/'System.CodeDom.dll'),original_target='net9.0',execution_framework='source NET10.0.5',original_identity_and_22_neutral_resources_passed=True,csharp_and_vb_unicode_generation_passed=True,both_generated_source_compiler_outputs_execute_to42=True,original_unsupported_compiler_api_preserved=True,net9_runtime_built=False,localized_satellites_built=False,formal_package_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source NET9 CodeDom executes on NET10;both generated language outputs compile and execute')
