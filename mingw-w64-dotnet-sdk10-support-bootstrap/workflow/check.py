"""Run original hashing vectors,resource/identity checks and SDK support integration."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;source=plan/'snapshot/runtime';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
vectors=[];inputs={}
for algorithm in ['Crc32','Crc64','XxHash32','XxHash64','XxHash3','XxHash128']:
    path=source/'src/libraries/System.IO.Hashing/tests'/(algorithm+'Tests.cs')
    if not path.exists():continue
    text=path.read_text(encoding='utf-8-sig');inputs[path.relative_to(source).as_posix()]=sha(path)
    for m in re.finditer(r'new TestCase\(\s*"([^"\n]*)",\s*"([0-9A-Fa-f]*)",\s*"([0-9A-Fa-f]+)"\s*\)',text):vectors.append(dict(algorithm=algorithm,name=m[1],input=m[2].upper(),expected=m[3].upper()))
assert len(vectors)>15,len(vectors);(out/'upstream-vectors.json').write_text(json.dumps(vectors)+'\n');binary=out/'bin';shutil.copytree(build/'bin',binary)
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
work=out/'native 世界';work.mkdir();(work/'Hello.cs').write_text('using System;class Hello {static void Main(string[] args){Console.WriteLine("SOURCE NET10 hello:"+Environment.Version+"|"+string.Join("|",args));}}')
config=json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5'))));(work/'Hello.runtimeconfig.json').write_text(config);(binary/'Check.runtimeconfig.json').write_text(config)
commands=[];env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_BUNDLE_EXTRACT_BASE_DIR=native(out/'bundle-cache'))
def run(label,cmd,environment=env):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=environment,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
for name,target,files,extra in [('hello',work/'Hello.dll',[work/'Hello.cs'],[]),('consumer',binary/'Check.dll',[here/'Check.cs'],list(binary.glob('*.dll')))]:
    args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(target)+'"']+['/reference:"'+native(p)+'"' for p in refs+extra]+['"'+native(p)+'"' for p in files]
    rsp=out/(name+'.rsp');rsp.write_text('\n'.join(args)+'\n');run(name,[host,compiler,'-noconfig','@'+native(rsp)])
template=prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Host.win-x64/8.0.31/runtimes/win-x64/native/apphost.exe';assert template.is_file()
cmd=[host,binary/'Check.dll',out/'upstream-vectors.json',source,work,template];run('execute',cmd)
run('hash-software-fallback',cmd+['--hash-only'],dict(env,DOTNET_EnableHWIntrinsic='0'))
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_upstream_vector_source_sha256=inputs,original_upstream_hash_vectors=len(vectors),software_intrinsic_fallback_checked=True,original_native_apphost_template_sha256=sha(template),native_template_original_framework='net8.0',generated_application_framework='net10.0',owned_unicode_apphost_and_bundle_execution=True,original_resource_values_checked=True,other_original_framework_profiles_built=False,full_upstream_test_suite_run=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'));print((out/'hash-software-fallback.log').read_text(encoding='utf-8'))
