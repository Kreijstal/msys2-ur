"""Execute resolver, template locator and file-based ProjectTools against owned fixtures."""
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
 wrapper=prefix/'lib/dotnet10/build-packs/sdk-cli-foundation-10.0.201-net10-bootstrap/bin/Microsoft.DotNet.NativeWrapper.dll';shutil.copyfile(wrapper,binary/wrapper.name)
 # The original NativeWrapper explicitly preloads x64/hostfxr.dll on Windows.
 fxr=prefix/'lib/dotnet10/host/fxr/10.0.5/hostfxr.dll';(binary/'x64').mkdir();shutil.copyfile(fxr,binary/'x64/hostfxr.dll');assert hashlib.sha256(fxr.read_bytes()).digest()==hashlib.sha256((binary/'x64/hostfxr.dll').read_bytes()).digest()
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167;references={p.name:p for p in refs}
for p in binary.glob('*.dll'):references[p.name]=p
key=out/'friend.snk';key.write_bytes(bytes.fromhex((here/'MicrosoftAspNetCore.pubkey.hex').read_text()));
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/nullable:enable','/langversion:preview','/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(binary/'dotnet.Tests.dll')+'"']+['/reference:"'+native(p)+'"' for p in references.values()]+['"'+native(here/'Check.cs')+'"'])+'\n');(binary/'dotnet.Tests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net10.0','framework':{'name':'Microsoft.NETCore.App','version':'10.0.5'}}}));work=out/'work 世界';work.mkdir();env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'));commands=[]
for label,cmd in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,binary/'dotnet.Tests.dll',prefix,source])]:
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,cwd=work,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_three_NET10_libraries_executed=True,signed_original_friend_identity_used=True,resolver_settings_and_native_pinned_SDK8_selection_passed=True,upstream_template_manifest_and_owned_installed_template_filtering_passed=True,original_Roslyn53_file_directives_and_errors_passed=True,owned_Unicode_project_generation_removal_and_selection_passed=True,original_AOT_and_tool_defaults_preserved=True,source_hostfxr_sha256=hashlib.sha256(fxr.read_bytes()).hexdigest(),full_SDK10_file_app_build_verified=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))
