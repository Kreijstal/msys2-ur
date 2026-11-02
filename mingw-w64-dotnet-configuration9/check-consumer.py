"""Execute original configuration, typed settings and protected XML APIs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
build,refs,out=(Path(p).resolve() for p in sys.argv[1:4]);feed=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else None;assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='System.Configuration.ConfigurationManager.dll';shutil.copyfile(build/name,out/name);shutil.copyfile(build/'neutral-strings.json',out/'neutral-strings.json');ref_files=sorted(refs.glob('*.dll'));assert len(ref_files)==164
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host));commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
if feed is None:feed=prefix/'lib/dotnet/library-packs'
dependency_assets={}
for dep in ['System.Diagnostics.EventLog','System.Security.Cryptography.ProtectedData']:
 package=feed/(dep.lower()+'.9.0.11.nupkg')
 with zipfile.ZipFile(package) as z:
  names=['runtimes/win/lib/net9.0/System.Diagnostics.EventLog.dll','runtimes/win/lib/net9.0/System.Diagnostics.EventLog.Messages.dll'] if dep=='System.Diagnostics.EventLog' else ['lib/net9.0/System.Security.Cryptography.ProtectedData.dll']
  for member in names:(out/Path(member).name).write_bytes(z.read(member))
 dependency_assets[dep]=dict(version='9.0.11',source_package_sha256=sha(package),assets={member:sha(out/Path(member).name) for member in names})
args=['/nostdlib+','/target:exe','/langversion:13.0','/nullable:enable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in ref_files+[out/name,out/'System.Diagnostics.EventLog.dll',out/'System.Security.Cryptography.ProtectedData.dll']],'"'+native(here/'inputs/Probe.cs')+'"'];rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8');run('compile-probe',[host,compiler,'-noconfig','@'+native(rsp)]);(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
run('execute',[host,out/'Probe.dll',native(out)]);(out/'results.json').write_text(json.dumps(dict(commands=commands,source_library_sha256=sha(out/name),original_target='net9.0',execution_framework='source NET10.0.5',dependency_assets=dependency_assets,configuration_roundtrips_typed_sections_settings_dpapi_and_errors_passed=True,original_rsa_provider_pnse_preserved=True,concurrent_independent_loads=12,formal_package_built=False,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('PASS source ConfigurationManager9 NET9 consumer with exact source EventLog/ProtectedData9')
