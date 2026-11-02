"""Validate and execute each distinct original CodePages4.5.1 implementation."""
from pathlib import Path
import argparse,functools,hashlib,json,os,shutil,subprocess,zipfile
p=argparse.ArgumentParser();p.add_argument('producer',type=Path);p.add_argument('out',type=Path);p.add_argument('compiler',type=Path);p.add_argument('--feed',type=Path);p.add_argument('--only-profile');args=p.parse_args()
root,out,compiler=(s.resolve() for s in [args.producer,args.out,args.compiler]);assert not out.exists();out.mkdir();here=Path(__file__).parent;library='System.Text.Encoding.CodePages';manifest=json.loads((here/'original-profile-requirements-20261031.json').read_text())
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dotnet='/clang64/lib/dotnet/dotnet.exe';driver=next(compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file());feed=Path('/clang64/lib/dotnet/library-packs')
feeds=list(dict.fromkeys(([native(args.feed.resolve())] if args.feed else [])+[native(feed)]));config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="feed'+str(i)+'" value="'+v+'"/>' for i,v in enumerate(feeds))+'</packageSources>'+('<packageSourceMapping><packageSource key="feed0"><package pattern="System.Text.Encoding.CodePages"/></packageSource><packageSource key="feed'+str(len(feeds)-1)+'"><package pattern="*"/></packageSource></packageSourceMapping>' if len(feeds)>1 else '')+'</configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-10000:])
host=out/'host';host.mkdir()
for n in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/n,host/n)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
run('host-build',[dotnet,'build',native(host/'Check.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']);checker=host/'bin/Release/net8.0/Check.dll';package=next((p for p in args.feed.glob('*.nupkg') if p.name.lower()=='system.text.encoding.codepages.4.5.1.nupkg'),None) if args.feed else None
if args.feed:assert package is not None
selected=manifest['profiles'] if args.only_profile is None else {args.only_profile:manifest['profiles'][args.only_profile]}
for profile,spec in selected.items():
 folder=out/profile;folder.mkdir();candidate=folder/(library+'.dll');asset=spec['original_paths'][0]
 if package:
  with zipfile.ZipFile(package) as z:candidate.write_bytes(z.read(asset))
 else:shutil.copy2(root/'profiles'/profile/'bin/Release'/(library+'.dll'),candidate)
 refs=sorted(Path('/clang64/lib/dotnet/reference-packs/netcore20-contracts-bootstrap/ref' if profile=='netcore2-windows' else '/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==(10 if profile=='netcore2-windows' else 113)
 if not profile.startswith('legacy'):
  with zipfile.ZipFile(feed/'system.runtime.compilerservices.unsafe.4.5.2.nupkg') as z:(folder/'System.Runtime.CompilerServices.Unsafe.dll').write_bytes(z.read('lib/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'))
 rsp=folder/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/unsafe+','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(folder/'Bridge.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[candidate]]+['"'+native(here/'inputs/Bridge.cs')+'"'])+'\n')
 run('bridge-'+profile,[dotnet,native(driver),'-noconfig','@'+native(rsp)])
 run('check-'+profile,[dotnet,native(checker),native(candidate),native(here/'inputs'/(asset.replace('/','_')+'.json')),native(here/'inputs/published-native-resources.json'),asset,'windows' if profile.endswith('windows') else 'default']);print((out/('check-'+profile+'.log')).read_text(),flush=True)
if package:
 for rid in ['', 'win-x64']:
  label='consumer-windows' if rid else 'consumer-portable';consumer=out/label;consumer.mkdir();shutil.copy2(here/'inputs/Bridge.cs',consumer/'Bridge.cs')
  (consumer/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><LangVersion>7.3</LangVersion><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit>'+('<RuntimeIdentifier>'+rid+'</RuntimeIdentifier>' if rid else '')+'</PropertyGroup><ItemGroup><PackageReference Include="System.Text.Encoding.CodePages" Version="[4.5.1]"/></ItemGroup></Project>\n')
  run(label+'-build',[dotnet,'build',native(consumer/'Bridge.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
  assets=json.loads((consumer/'obj/project.assets.json').read_text());assert not assets.get('logs');assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0','System.Text.Encoding.CodePages/4.5.1','System.Runtime.CompilerServices.Unsafe/4.5.2'}
  for n,version in [('system.text.encoding.codepages','4.5.1'),('system.runtime.compilerservices.unsafe','4.5.2')]:
   archive=package if n=='system.text.encoding.codepages' else feed/(n+'.'+version+'.nupkg');assert (out/'cache'/n/version/(n+'.'+version+'.nupkg')).read_bytes()==archive.read_bytes()
  key='.NETStandard,Version=v2.0'+('/'+rid if rid else '');selected_asset=assets['targets'][key]['System.Text.Encoding.CodePages/4.5.1'];assert set(selected_asset['compile'])=={'lib/netstandard2.0/System.Text.Encoding.CodePages.dll'}
  runtime_path='runtimes/win/lib/netstandard2.0/System.Text.Encoding.CodePages.dll' if rid else 'lib/netstandard2.0/System.Text.Encoding.CodePages.dll'
  if rid:assert set(selected_asset['runtime'])=={runtime_path}
  else:assert set(selected_asset['runtime'])=={runtime_path}
  owned=out/(label+'-owned');owned.mkdir();shutil.copy2(consumer/'bin/Release/netstandard2.0'/rid/'Bridge.dll' if rid else consumer/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
  with zipfile.ZipFile(package) as z:(owned/(library+'.dll')).write_bytes(z.read(runtime_path))
  with zipfile.ZipFile(feed/'system.runtime.compilerservices.unsafe.4.5.2.nupkg') as z:(owned/'System.Runtime.CompilerServices.Unsafe.dll').write_bytes(z.read('lib/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'))
  run(label+'-run',[dotnet,native(checker),native(owned/(library+'.dll')),native(here/'inputs'/(runtime_path.replace('/','_')+'.json')),native(here/'inputs/published-native-resources.json'),runtime_path,'windows' if rid else 'default']);print((out/(label+'-run.log')).read_text(),flush=True)
 marker=out/'net8-rid-restore';marker.mkdir();(marker/'Restore.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><RuntimeIdentifier>win-x64</RuntimeIdentifier><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><PackageReference Include="System.Text.Encoding.CodePages" Version="[4.5.1]"/></ItemGroup></Project>\n')
 run('net8-rid-restore',[dotnet,'restore',native(marker/'Restore.csproj'),'--configfile',native(config),'-v:minimal'])
 assets=json.loads((marker/'obj/project.assets.json').read_text());assert not assets.get('logs');assert set(assets['libraries'])=={'System.Text.Encoding.CodePages/4.5.1','System.Runtime.CompilerServices.Unsafe/4.5.2','Microsoft.NETCore.Platforms/2.1.2'}
 selected_asset=assets['targets']['net8.0/win-x64']['System.Text.Encoding.CodePages/4.5.1'];assert set(selected_asset['compile'])=={'lib/netstandard2.0/System.Text.Encoding.CodePages.dll'} and set(selected_asset['runtime'])=={'runtimes/win/lib/netcoreapp2.0/System.Text.Encoding.CodePages.dll'}
 assert (out/'cache/microsoft.netcore.platforms/2.1.2/microsoft.netcore.platforms.2.1.2.nupkg').read_bytes()==(feed/'microsoft.netcore.platforms.2.1.2.nupkg').read_bytes()
 print('PASS NET8 Windows restore selects original Core2 runtime asset and exact Platforms2.1.2 source archive',flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_distinct_implementations=5,validated_profiles=list(selected),all_five_implementations_verified=len(selected)==5,original_DLL_asset_paths=8,original_API_entries_per_implementation=5,original_identity_dependency_resource_and_managed_native_metadata_verified=True,exact_candidate_implementations_and_newer_Unsafe_dependency_executed=True,exact_bytes_multibyte_stateful_fallback_streaming_concurrency_platform_ACP_checks_passed=True,source_NET8_runtime_host=True,fresh_NS2_portable_and_Windows_exact_compile_runtime_selection_and_execution_passed=package is not None,fresh_NET8_Windows_restore_original_Core2_runtime_asset_and_Platforms212_selected=package is not None,package_sha256=sha(package) if package else None,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
