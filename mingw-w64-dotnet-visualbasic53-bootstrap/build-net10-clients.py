"""Build original NET10 vbc and VBCSCompiler using the newly built NET10 csc."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,shutil,subprocess,sys,xml.etree.ElementTree as E
source,plan,csharp,vb,out=(Path(p).resolve() for p in sys.argv[1:6]);assert not out.exists();out.mkdir()
@lru_cache(maxsize=None)
def native(p):
 s=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',s):return s[1].upper()+':'+s[2:]
 if s.startswith('/clang64/'):return native(Path('/clang64'))+s[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',s],text=True).strip()
source_native=native(source)
def local(value):
 value=value.replace('\\','/');assert value.lower().startswith(source_native.lower()+'/')
 return source/value[len(source_native)+1:]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binary=out/'bin';shutil.copytree(csharp/'bin',binary)
for n in ['Microsoft.CodeAnalysis.VisualBasic.dll','Microsoft.CodeAnalysis.VisualBasic.pdb']:shutil.copyfile(vb/n,binary/n)
model=json.loads((plan/'evaluated.json').read_text());refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
refs += [binary/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.VisualBasic']]
settings=E.parse(source/'eng/targets/Settings.props');key=settings.findtext('.//MicrosoftSharedPublicKey');assert key and re.fullmatch('[0-9a-fA-F]+',key)
(out/'Roslyn.public.snk').write_bytes(bytes.fromhex(key))
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable');records={}
for name in ['vbc','VBCSCompiler']:
 entry=model[name];assert entry['properties']['TargetFramework']=='net10.0'
 folder=out/name;folder.mkdir();files=[local(i['full_path']) for i in entry['items']['Compile']]
 attrs=['[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]','[assembly:System.Reflection.AssemblyFileVersion("5.3.0.0")]','[assembly:System.Reflection.AssemblyInformationalVersion("5.3.0-2.26113.113+2333221c0564852ee5ceac9c622a0b14e864d76e")]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]','[assembly:Microsoft.CodeAnalysis.CommitHash("2333221c0564852ee5ceac9c622a0b14e864d76e")]']
 for item in entry['items']['InternalsVisibleTo']:attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+(item['metadata'].get('Key') or key))+')]')
 info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n')
 defines=list(dict.fromkeys([d for d in re.split('[;,]',entry['properties']['DefineConstants']) if d]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]))
 args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:enable','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Roslyn.public.snk')+'"','/out:"'+native(binary/(name+'.dll'))+'"','/define:'+';'.join(defines)]
 args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in files+[info]]
 rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
 command=[host,native(binary/'csc.dll'),'-noconfig','@'+native(rsp)]
 with (folder/'compile.log').open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0,(name,r.returncode)
 shutil.copyfile(binary/'csc.runtimeconfig.json',binary/(name+'.runtimeconfig.json'))
 records[name]=dict(original_sources_sha256={p.relative_to(source).as_posix():sha(p) for p in files},actual_references_sha256={str(p):sha(p) for p in refs},output_sha256=sha(binary/(name+'.dll')),command=command,compile_exit_code=0,original_target='net10.0',execution_verified=False)
 print('PASS original NET10 tool compilation:',name,flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,all_six_original_net10_compiler_projects_compiled=True,visualbasic_localized_satellites_built=False,compiler_server_execution_verified=False,formal_full_toolset_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
