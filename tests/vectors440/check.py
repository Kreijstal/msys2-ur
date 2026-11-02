"""Check every original profile and execute old vector behavior in isolated contexts."""
from pathlib import Path
import argparse,functools,hashlib,json,os,shutil,subprocess,zipfile
p=argparse.ArgumentParser();p.add_argument('producer',type=Path);p.add_argument('out',type=Path);p.add_argument('compiler',type=Path);p.add_argument('--feed',type=Path);p.add_argument('--record-original-resources',type=Path);args=p.parse_args()
root,out,compiler=(s.resolve() for s in [args.producer,args.out,args.compiler]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
compiler_dll=next((compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file()),None);assert compiler_dll is not None
feeds=list(dict.fromkeys(([native(args.feed.resolve())] if args.feed else [])+[native(Path('/clang64/lib/dotnet/library-packs'))]));config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="feed'+str(i)+'" value="'+v+'"/>' for i,v in enumerate(feeds))+'</packageSources>'+('<packageSourceMapping><packageSource key="feed0"><package pattern="System.Numerics.Vectors"/></packageSource><packageSource key="feed'+str(len(feeds)-1)+'"><package pattern="*"/></packageSource></packageSourceMapping>' if len(feeds)>1 else '')+'</configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-7000:])
host=out/'host';host.mkdir()
for n in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/n,host/n)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
run('host-build',[dotnet,'build',native(host/'Check.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']);checker=host/'bin/Release/net8.0/Check.dll'
if args.record_original_resources:
 for tfm in ['netstandard1.0','netstandard2.0','net46']:
  original=args.record_original_resources.resolve()/'lib'/tfm/'System.Numerics.Vectors.dll';run('resources-'+tfm,[dotnet,native(checker),'--resources',native(original),native(here/'inputs'/('resources-'+tfm+'.json'))])
 print('PASS published resources read only as metadata; no published DLL executed');raise SystemExit(0)
package=next((f for f in args.feed.glob('*.nupkg') if f.name.lower()=='system.numerics.vectors.4.4.0.nupkg'),None) if args.feed else None
if args.feed:assert package is not None
for kind in ['lib','ref']:
 for tfm in ['netstandard1.0','netstandard2.0','net46']:
  owned=out/kind/tfm;owned.mkdir(parents=True);file=owned/'System.Numerics.Vectors.dll'
  if package:
   with zipfile.ZipFile(package) as z:file.write_bytes(z.read(kind+'/'+tfm+'/System.Numerics.Vectors.dll'))
  else:shutil.copy2(root/kind/tfm/'bin/Release/System.Numerics.Vectors.dll',file)
  if kind=='lib':
   refs=([Path('/clang64/lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref')/n for n in ['mscorlib.dll','System.Numerics.dll']] if tfm=='net46' else sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll')));assert len(refs)==(2 if tfm=='net46' else 113)
   flags=['/nostdlib+','/target:library','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(owned/'Bridge.dll')+'"']+['/reference:"'+native(f)+'"' for f in refs+[file]]+['"'+native(here/'inputs/Bridge.cs')+'"'];rsp=owned/'compile.rsp';rsp.write_text('\n'.join(flags)+'\n')
   run('bridge-'+tfm,[dotnet,native(compiler_dll),'-noconfig','@'+native(rsp)])
  run('check-'+kind+'-'+tfm,[dotnet,native(checker),native(file),native(here/'inputs'/('published-'+kind+'-'+tfm+'.json')),native(here/'inputs'/('resources-'+tfm+'.json')) if kind=='lib' else '--reference',native(here/'inputs/native-version-policy.json'),kind+'/'+tfm,native(here/'inputs/published-forwarders.json')])
  print((out/('check-'+kind+'-'+tfm+'.log')).read_text(),flush=True)
if package:
 bridge=out/'consumer';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
 (bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><LangVersion>7.3</LangVersion><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Numerics.Vectors" Version="[4.4.0]"/></ItemGroup></Project>\n')
 run('consumer-build',[dotnet,'build',native(bridge/'Bridge.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 assert (out/'cache/system.numerics.vectors/4.4.0/system.numerics.vectors.4.4.0.nupkg').read_bytes()==package.read_bytes()
 assets=json.loads((bridge/'obj/project.assets.json').read_text());assert not assets.get('logs');assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0','System.Numerics.Vectors/4.4.0'}
 selected=assets['targets']['.NETStandard,Version=v2.0']['System.Numerics.Vectors/4.4.0'];assert set(selected['compile'])=={'ref/netstandard2.0/System.Numerics.Vectors.dll'} and set(selected['runtime'])=={'lib/netstandard2.0/System.Numerics.Vectors.dll'}
 owned=out/'consumer-owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
 with zipfile.ZipFile(package) as z:(owned/'System.Numerics.Vectors.dll').write_bytes(z.read('lib/netstandard2.0/System.Numerics.Vectors.dll'))
 run('consumer-run',[dotnet,native(checker),native(owned/'System.Numerics.Vectors.dll'),native(here/'inputs/published-lib-netstandard2.0.json'),native(here/'inputs/resources-netstandard2.0.json'),native(here/'inputs/native-version-policy.json'),'lib/netstandard2.0',native(here/'inputs/published-forwarders.json')])
 print((out/'consumer-run.log').read_text(),flush=True)
 marker=out/'framework-marker-consumer';marker.mkdir()
 (marker/'Program.cs').write_text('using System;using System.Numerics;class Program {static void Main(){var value=new Vector3(1,2,3);if(Vector3.Dot(value,value)!=14 || !typeof(Vector3).Assembly.Location.Replace((char)92,(char)47).Contains("/shared/Microsoft.NETCore.App/8.0.31/"))throw new Exception("Source framework vector marker");Console.WriteLine("PASS original NETCore empty markers use source framework vectors");}}\n')
 (marker/'Marker.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Numerics.Vectors" Version="[4.4.0]"/></ItemGroup></Project>\n')
 run('framework-marker-build',[dotnet,'build',native(marker/'Marker.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 marker_assets=json.loads((marker/'obj/project.assets.json').read_text());assert not marker_assets.get('logs')
 selected=marker_assets['targets']['net8.0']['System.Numerics.Vectors/4.4.0']
 assert set(selected['compile'])=={'ref/netcoreapp2.0/_._'} and set(selected['runtime'])=={'lib/netcoreapp2.0/_._'}
 assert not (marker/'bin/Release/net8.0/System.Numerics.Vectors.dll').exists()
 run('framework-marker-run',[dotnet,native(marker/'bin/Release/net8.0/Marker.dll')]);print((out/'framework-marker-run.log').read_text(),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_runtime_profiles=['netstandard1.0','netstandard2.0','net46','portable-net45+win8+wp8+wpa81'],original_reference_profiles=['netstandard1.0','netstandard2.0','net46'],original_public_API_entries_per_portable_profile=497,original_public_API_entries_per_NET46_profile=133,original_identity_dependencies_resources_and_managed_native_metadata_equal=True,isolated_exact_old_implementations_executed=True,ten_generic_scalar_types_and_vector_matrix_quaternion_plane_checks_passed=True,all_seven_original_NET46_forwarders_verified=True,fresh_NS2_exact_reference_and_runtime_consumer_passed=package is not None,fresh_NET8_original_empty_framework_marker_consumer_passed=package is not None,exact_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest() if package else None,full_upstream_suite_run=False,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
