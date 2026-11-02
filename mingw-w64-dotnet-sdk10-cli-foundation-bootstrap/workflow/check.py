"""Execute actual CLI helper libraries against owned files and source native hostfxr/MSI queries."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
plan,build,out=(Path(p).resolve() for p in sys.argv[1:4]);installed_runtime=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None;out.mkdir();here=Path(__file__).resolve().parent;source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();binary=out/'bin';fxr=prefix/'lib/dotnet10/host/fxr/10.0.5/hostfxr.dll'
if installed_runtime is not None:shutil.copytree(installed_runtime,binary)
else:
 shutil.copytree(build/'bin',binary)
 for p in (build/'dependency-assets').glob('*.dll'):shutil.copyfile(p,binary/p.name)
 msbuild=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap'
 for p in msbuild.glob('*.dll'):
  if not (binary/p.name).exists():shutil.copyfile(p,binary/p.name)
 # The original NativeWrapper explicitly preloads x64/hostfxr.dll on Windows.
 fxr=prefix/'lib/dotnet10/host/fxr/10.0.5/hostfxr.dll';(binary/'x64').mkdir();shutil.copyfile(fxr,binary/'x64/hostfxr.dll');assert hashlib.sha256(fxr.read_bytes()).digest()==hashlib.sha256((binary/'x64/hostfxr.dll').read_bytes()).digest()
 # Runtime assets are the real source package implementations.
 feed=prefix/'lib/dotnet/library-packs'
 for name,version,member in [('System.Security.Cryptography.Pkcs','8.0.1','runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'),('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll')]:
  archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower())
  with zipfile.ZipFile(archive) as z:(binary/(name+'.dll')).write_bytes(z.read(member))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167;references={p.name:p for p in refs}
for p in binary.glob('*.dll'):references[p.name]=p
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/nullable:enable','/langversion:preview','/out:"'+native(binary/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in references.values()]+['"'+native(here/'Check.cs')+'"'])+'\n');(binary/'Check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net10.0','framework':{'name':'Microsoft.NETCore.App','version':'10.0.5'}}}));work=out/'work 世界';work.mkdir();env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'));commands=[]
for label,cmd in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,binary/'Check.dll',prefix,source])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,cwd=work,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_eight_NET10_libraries_executed=True,owned_path_sentinel_cache_retry_passed=True,original_span_parser_and_MSBuild_forwarding_passed=True,original_five_shell_generators_executed=True,unchanged_upstream_manifest_passed=True,owned_Unicode_invalid_manifest_and_RID_alias_passed=True,source_hostfxr_SDK_runtime_enumeration_resolution_and_16_GC_callbacks_passed=True,source_hostfxr_sha256=hashlib.sha256(fxr.read_bytes()).hexdigest(),native_MSI_read_only_error_queries_passed=True,MSI_install_write_operations_verified=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))
