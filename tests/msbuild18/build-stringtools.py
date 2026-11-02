"""Compile original NET10 StringTools selected by the MSBuild project model."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,subprocess,sys,zipfile
plan,out=(Path(p).resolve() for p in sys.argv[1:3]);framework=sys.argv[3:]==['--framework'];assert not sys.argv[3:] or framework
assert not out.exists();out.mkdir()
@lru_cache(maxsize=None)
def native(p):
 value=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',value):return value[1].upper()+':'+value[2:]
 if value.startswith('/clang64/'):return native(Path('/clang64'))+value[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',value],text=True).strip()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root'].replace('E:/','/e/'))
root_native=native(source)
def local(value):
 value=value.replace('\\','/');assert value.lower().startswith(root_native.lower()+'/'),value
 return source/value[len(root_native)+1:]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='Microsoft.Build.Framework' if framework else 'Microsoft.NET.StringTools'
entry=json.loads((plan/'evaluated.json').read_text())[name];assert entry['properties']['TargetFramework']=='net10.0'
files=list(dict.fromkeys(local(i['full_path']) for i in entry['items']['Compile']));assert len(files)==(179 if framework else 8)
originals={p.relative_to(source).as_posix():sha(p) for p in files}
source_packages={}
if framework:
 package=plan.parent/'msbuild-source-packages/microsoft.codeanalysis.contracts.5.0.0-1.25277.114.nupkg'
 assert sha(package)=='7613b5ba957ba01667db49d98d89363315eaf14114213bab185012d3424c0b10'
 folder=out/'contracts-source';folder.mkdir()
 with zipfile.ZipFile(package) as archive:
  for n in archive.namelist():
   if n.endswith('/'):continue
   data=archive.read(n);assert not data.startswith(b'MZ'),n
   assert not n.lower().endswith(('.dll','.exe','.so','.dylib')),n
   if n.startswith('contentFiles/cs/net9.0/') and n.endswith('.cs'):
    path=folder/n.removeprefix('contentFiles/cs/net9.0/');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);files.append(path);source_packages[n]=hashlib.sha256(data).hexdigest()
 assert len(source_packages)==19,len(source_packages)
keys=re.findall('PublicKey=([0-9a-f]+)',(source/'src/StringTools/AssemblyInfo.cs').read_text(encoding='utf-8-sig'))
key=keys[-1];assert hashlib.sha1(bytes.fromhex(key)).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
(out/'Microsoft.public.snk').write_bytes(bytes.fromhex(key))
assembly_version='15.1.0.0' if framework else '1.0.0.0'
info=out/'AssemblyInfo.g.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("'+assembly_version+'") ]\n[assembly:System.Reflection.AssemblyFileVersion("18.3.0.0")]\n[assembly:System.Reflection.AssemblyInformationalVersion("18.3.0-release-26113-113+228caa11ad0046ccb599530abd9aba4e1979b5e9")]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]\n');files.append(info)
defines=list(dict.fromkeys([d for d in entry['properties']['DefineConstants'].split(';') if d]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]))
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:library','/langversion:preview','/nullable:enable','/unsafe+','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Microsoft.public.snk')+'"','/out:"'+native(out/(name+'.dll'))+'"','/define:'+';'.join(defines)]
args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in files]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
host='/clang64/lib/dotnet10/dotnet.exe';compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll');env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_HOST_PATH=native(Path(host)))
command=[host,native(compiler),'-noconfig','@'+native(rsp)]
with (out/'compile.log').open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'compile.log')
(out/'results.json').write_text(json.dumps(dict(project=name,command=command,compile_exit_code=0,original_source_hashes=originals,source_package_inputs_sha256=source_packages,actual_compile_inputs_sha256={str(p):sha(p) for p in files},actual_reference_hashes={str(p):sha(p) for p in refs},compiler_sha256=sha(compiler),output_sha256=sha(out/(name+'.dll')),original_target='net10.0',assembly_version=assembly_version,public_key_token='b03f5f7f11d50a3a',bootstrap_file_version='18.3.0.0',original_arcade_file_version_calculated=False,original_production_source_changes=0,executed=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NET10',name,'compilation:',len(originals),'unchanged source files;',len(source_packages),'exact source-package inputs;original Arcade file-version task still pending')
