"""Compile original NET10 Roslyn tasks against source MSBuild17.11 APIs."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as E

plan,msbuild,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']).resolve()
entry=json.loads((plan/'evaluated.json').read_text())['Microsoft.Build.Tasks.CodeAnalysis']
assert entry['properties']['TargetFramework']=='net10.0'
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe'
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host))
commands=[]
def run(label,command,environment=env):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']))
assert len(files)==60 and all(p.is_relative_to(source) for p in files)
originals={p.relative_to(source).as_posix():sha(p) for p in files}
settings=E.parse(source/'eng/targets/Settings.props')
key=settings.findtext('.//MicrosoftSharedPublicKey');assert key
keyfile=out/'Roslyn.public.snk';keyfile.write_bytes(bytes.fromhex(key))
assert hashlib.sha1(keyfile.read_bytes()).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
resources=[];resource_inputs={}
p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));t=E.SubElement(p,'Target',Name='Generate')
for i in entry['items']['EmbeddedResource']:
    resx=Path(i['full_path']).resolve();assert resx.suffix=='.resx'
    resource_inputs[resx.relative_to(source).as_posix()]=sha(resx)
    logical='Microsoft.CodeAnalysis.BuildTasks.'+resx.stem
    binary=out/(logical+'.resources');E.SubElement(t,'GenerateResource',Sources=native(resx),OutputResources=native(binary),ExecuteAsTool='false');resources.append((binary,logical+'.resources'))
    wrapper=out/(resx.stem+'.g.cs');nodes=list(E.parse(resx).iter('data'))
    wrapper.write_text('namespace Microsoft.CodeAnalysis.BuildTasks { internal static class '+resx.stem+' { internal static System.Resources.ResourceManager ResourceManager { get; } = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof('+resx.stem+').Assembly);\n'+''.join('internal static string '+re.sub(r'[^A-Za-z0-9_]','_',n.get('name'))+' => ResourceManager.GetString('+json.dumps(n.get('name'))+')!;\n' for n in nodes)+'}}\n')
    files.append(wrapper)
E.ElementTree(p).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
run('resources',[host8,'msbuild',out/'Resources.proj','-t:Generate','-nologo'],dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent)))
info=out/'AssemblyInfo.g.cs'
info.write_text('[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyInformationalVersion("5.3.0-2.26113.113+2333221c0564852ee5ceac9c622a0b14e864d76e")]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]\n[assembly:Microsoft.CodeAnalysis.CommitHash("2333221c0564852ee5ceac9c622a0b14e864d76e")]\n')
files.append(info)
for n in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.Build.Tasks.Core','Microsoft.NET.StringTools']:
    r=json.loads((msbuild/n/'results.json').read_text());dll=msbuild/n/(n+'.dll');assert sha(dll)==r['output_sha256'];refs.append(dll)
defines=list(dict.fromkeys(entry['properties']['DefineConstants'].split(';')+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]+['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]))
destination=out/'Microsoft.Build.Tasks.CodeAnalysis.dll'
args=['/nostdlib+','/target:library','/langversion:preview','/unsafe+','/nullable:enable','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(keyfile)+'"','/out:"'+native(destination)+'"','/define:'+';'.join(defines)]
args+=['/reference:"'+native(p)+'"' for p in refs]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
run('compile',[host,compiler,'-noconfig','@'+native(rsp)])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_source_sha256=originals,original_resource_sha256=resource_inputs,actual_reference_sha256={native(p):sha(p) for p in refs},output_sha256=sha(destination),original_target_framework='net10.0',original_compile_time_msbuild_source_version='17.11.48',original_production_source_changes=0,msbuild17_source_sdk8_bootstrap_closure_used=True,formal_exact_msbuild17_dependency_packages_resolved=False,formal_task_package_built=False,task_execution_verified=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NET10 Roslyn MSBuild tasks,60 unchanged sources,source MSBuild17.11.48 compile-time APIs')
