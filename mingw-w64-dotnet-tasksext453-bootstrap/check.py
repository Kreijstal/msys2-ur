"""Check Tasks.Extensions4.5.3 metadata and execute each exact old source implementation."""
from pathlib import Path
import argparse,functools,hashlib,json,os,shutil,subprocess,zipfile

p=argparse.ArgumentParser();p.add_argument('producer',type=Path);p.add_argument('out',type=Path);p.add_argument('compiler',type=Path);p.add_argument('--feed',type=Path);args=p.parse_args()
root,out,compiler=(s.resolve() for s in [args.producer,args.out,args.compiler]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
driver=next(compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file());dotnet='/clang64/lib/dotnet/dotnet.exe'
feed=Path('/clang64/lib/dotnet/library-packs');feeds=list(dict.fromkeys(([native(args.feed.resolve())] if args.feed else [])+[native(feed)]));config=out/'NuGet.config'
config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="feed'+str(i)+'" value="'+v+'"/>' for i,v in enumerate(feeds))+'</packageSources>'+('<packageSourceMapping><packageSource key="feed0"><package pattern="System.Threading.Tasks.Extensions"/></packageSource><packageSource key="feed'+str(len(feeds)-1)+'"><package pattern="*"/></packageSource></packageSourceMapping>' if len(feeds)>1 else '')+'</configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[];dependencies={}
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-9000:])
host=out/'host';host.mkdir()
for n in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/n,host/n)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
run('host-build',[dotnet,'build',native(host/'Check.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']);checker=host/'bin/Release/net8.0/Check.dll'
package=None
if args.feed:package=next(f for f in args.feed.glob('*.nupkg') if f.name.lower()=='system.threading.tasks.extensions.4.5.3.nupkg')
for tfm in ['netstandard1.0','netstandard2.0']:
 owned=out/tfm;owned.mkdir();candidate=owned/'System.Threading.Tasks.Extensions.dll'
 if package:
  with zipfile.ZipFile(package) as z:candidate.write_bytes(z.read('lib/'+tfm+'/System.Threading.Tasks.Extensions.dll'))
 else:shutil.copy2(root/'lib'/tfm/'bin/Release/System.Threading.Tasks.Extensions.dll',candidate)
 refs=sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==113
 selected=[('system.runtime.compilerservices.unsafe.4.5.2.nupkg','System.Runtime.CompilerServices.Unsafe',tfm,tfm)]
 dependencies[tfm]={}
 for archive,name,compile_tfm,runtime_tfm in selected:
  compile_file=owned/'source-references'/(name+'.dll');compile_file.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(feed/archive) as z:
   compile_file.write_bytes(z.read('ref/'+compile_tfm+'/'+name+'.dll'));(owned/(name+'.dll')).write_bytes(z.read('lib/'+runtime_tfm+'/'+name+'.dll'))
  refs.append(compile_file);dependencies[tfm][archive]=dict(package_sha256=sha(feed/archive),compile_asset='ref/'+compile_tfm+'/'+name+'.dll',runtime_asset='lib/'+runtime_tfm+'/'+name+'.dll',runtime_DLL_sha256=sha(owned/(name+'.dll')))
 rsp=owned/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/unsafe+','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(owned/'Bridge.dll')+'"']+['/reference:"'+native(f)+'"' for f in refs+[candidate]]+['"'+native(here/'inputs'/n)+'"' for n in ['Bridge.cs','ManualResetValueTaskSource.cs']])+'\n')
 run('bridge-'+tfm,[dotnet,native(driver),'-noconfig','@'+native(rsp)])
 run('check-'+tfm,[dotnet,native(checker),native(candidate),native(here/'inputs'/('published-lib-'+tfm+'.json')),native(here/'inputs'/('resources-'+tfm+'.json')),native(here/'inputs/native-version-policy.json'),'lib/'+tfm]);print((out/('check-'+tfm+'.log')).read_text(),flush=True)
if package:
 consumer=out/'consumer';consumer.mkdir();shutil.copy2(here/'inputs/Bridge.cs',consumer/'Bridge.cs');shutil.copy2(here/'inputs/ManualResetValueTaskSource.cs',consumer/'ManualResetValueTaskSource.cs')
 (consumer/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><LangVersion>7.3</LangVersion><AllowUnsafeBlocks>true</AllowUnsafeBlocks><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Threading.Tasks.Extensions" Version="[4.5.3]"/></ItemGroup></Project>\n')
 run('consumer-build',[dotnet,'build',native(consumer/'Bridge.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 assets=json.loads((consumer/'obj/project.assets.json').read_text());assert not assets.get('logs')
 assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0','System.Threading.Tasks.Extensions/4.5.3','System.Runtime.CompilerServices.Unsafe/4.5.2'}
 for n,version in [('system.threading.tasks.extensions','4.5.3'),('system.runtime.compilerservices.unsafe','4.5.2')]:
  archive=package if n=='system.threading.tasks.extensions' else feed/(n+'.'+version+'.nupkg');assert (out/'cache'/n/version/(n+'.'+version+'.nupkg')).read_bytes()==archive.read_bytes()
 selected=assets['targets']['.NETStandard,Version=v2.0']['System.Threading.Tasks.Extensions/4.5.3'];assert set(selected['compile'])==set(selected['runtime'])=={'lib/netstandard2.0/System.Threading.Tasks.Extensions.dll'}
 owned=out/'consumer-owned';owned.mkdir();shutil.copy2(consumer/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
 for n in ['System.Threading.Tasks.Extensions','System.Runtime.CompilerServices.Unsafe']:shutil.copy2(out/'netstandard2.0'/(n+'.dll'),owned/(n+'.dll'))
 run('consumer-run',[dotnet,native(checker),native(owned/'System.Threading.Tasks.Extensions.dll'),native(here/'inputs/published-lib-netstandard2.0.json'),native(here/'inputs/resources-netstandard2.0.json'),native(here/'inputs/native-version-policy.json'),'lib/netstandard2.0']);print((out/'consumer-run.log').read_text(),flush=True)
 marker=out/'framework-marker-consumer';marker.mkdir()
 (marker/'Program.cs').write_text('using System;using System.Threading.Tasks;class Program {static void Main(){var task=new ValueTask<int>(7);if(task.Result!=7 || typeof(ValueTask<int>).Assembly.GetName().Name!="System.Private.CoreLib" || !typeof(ValueTask<int>).Assembly.Location.Replace((char)92,(char)47).Contains("/shared/Microsoft.NETCore.App/8.0.31/"))throw new Exception("Source framework ValueTask marker");Console.WriteLine("PASS original NETCore2.1 empty markers use source framework ValueTask");}}\n')
 (marker/'Marker.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Threading.Tasks.Extensions" Version="[4.5.3]"/></ItemGroup></Project>\n')
 run('framework-marker-build',[dotnet,'build',native(marker/'Marker.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 marker_assets=json.loads((marker/'obj/project.assets.json').read_text());assert not marker_assets.get('logs');assert set(marker_assets['libraries'])=={'System.Threading.Tasks.Extensions/4.5.3'}
 selected=marker_assets['targets']['net8.0']['System.Threading.Tasks.Extensions/4.5.3'];assert set(selected['compile'])=={'ref/netcoreapp2.1/_._'} and set(selected['runtime'])=={'lib/netcoreapp2.1/_._'}
 assert not (marker/'bin/Release/net8.0/System.Threading.Tasks.Extensions.dll').exists()
 run('framework-marker-run',[dotnet,native(marker/'bin/Release/net8.0/Marker.dll')]);print((out/'framework-marker-run.log').read_text(),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_runtime_profiles=['netstandard1.0','netstandard2.0'],original_public_API_entries_per_profile=115,original_identity_dependencies_resources_managed_native_metadata_equal=True,isolated_exact_old_TasksExtensions_Unsafe_implementations_executed=True,ValueTask_builder_source_conversion_fault_cancellation_continuation_context_token_and_64_races_passed=True,source_dependency_inputs=dependencies,fresh_NS2_exact_source_dependency_graph_and_compile_runtime_asset_selection_passed=package is not None,fresh_NET8_original_empty_framework_marker_consumer_passed=package is not None,package_sha256=sha(package) if package else None,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
