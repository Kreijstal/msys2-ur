"""Validate all original Unsafe profiles and execute every public method in isolation."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,zipfile,hashlib
parser=argparse.ArgumentParser();parser.add_argument('producer',type=Path);parser.add_argument('out',type=Path);parser.add_argument('compiler',type=Path);parser.add_argument('--record-original-body-metadata',type=Path);parser.add_argument('--feed',type=Path);args=parser.parse_args()
root,out,compiler=args.producer.resolve(),args.out.resolve(),args.compiler.resolve();assert not out.exists();out.mkdir();here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
compiler_dll=next((compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file()),None);assert compiler_dll is not None
config=out/'NuGet.config'
feeds=list(dict.fromkeys(([native(args.feed.resolve())] if args.feed else [])+[native(Path('/clang64/lib/dotnet/library-packs'))]))
config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="feed'+str(i)+'" value="'+value+'"/>' for i,value in enumerate(feeds))+'</packageSources>'+('<packageSourceMapping><packageSource key="feed0"><package pattern="System.Runtime.CompilerServices.Unsafe"/></packageSource><packageSource key="feed'+str(len(feeds)-1)+'"><package pattern="*"/></packageSource></packageSourceMapping>' if len(feeds)>1 else '')+'</configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-6000:])
host=out/'host';host.mkdir()
for n in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/n,host/n)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
run('host-build',[dotnet,'build',native(host/'Check.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']);checker=host/'bin/Release/net8.0/Check.dll'
if args.record_original_body_metadata:
 for tfm in ['netstandard1.0','netstandard2.0','netcoreapp2.0']:
  original=args.record_original_body_metadata.resolve()/'lib'/tfm/'System.Runtime.CompilerServices.Unsafe.dll'
  run('body-metadata-'+tfm,[dotnet,native(checker),'--bodies',native(original),native(here/'inputs'/('il-bodies-'+tfm+'.json'))])
 print('PASS published method bodies read as metadata only; no published assembly executed')
 raise SystemExit(0)
package=next((p for p in args.feed.glob('*.nupkg') if p.name.lower()=='system.runtime.compilerservices.unsafe.4.5.2.nupkg'),None) if args.feed else None
if args.feed:assert package is not None
for tfm in ['netstandard1.0','netstandard2.0','netcoreapp2.0']:
 owned=out/tfm;owned.mkdir()
 if package:
  with zipfile.ZipFile(package) as z:data=z.read('lib/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll')
 else:data=(root/tfm/'System.Runtime.CompilerServices.Unsafe.dll').read_bytes()
 (owned/'System.Runtime.CompilerServices.Unsafe.dll').write_bytes(data)
 refs=sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==113
 rsp=owned/'compile.rsp';flags=['/nostdlib+','/target:library','/unsafe+','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(owned/'Bridge.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[owned/'System.Runtime.CompilerServices.Unsafe.dll']]+['"'+native(here/'inputs/Bridge.cs')+'"'];rsp.write_text('\n'.join(flags)+'\n')
 run('bridge-'+tfm,[dotnet,native(compiler_dll),'-noconfig','@'+native(rsp)])
 run('run-'+tfm,[dotnet,native(checker),native(owned/'System.Runtime.CompilerServices.Unsafe.dll'),native(here/'inputs'/('published-'+tfm+'.json')),native(here/'inputs'/('il-bodies-'+tfm+'.json')),native(here/'inputs/version-policy.json')])
 print((out/('run-'+tfm+'.log')).read_text(),flush=True)
for tfm in ['netstandard1.0','netstandard2.0']:
 file=root/'ref'/tfm/'System.Runtime.CompilerServices.Unsafe.dll'
 if package:
  file=out/('ref-'+tfm)/'System.Runtime.CompilerServices.Unsafe.dll';file.parent.mkdir()
  with zipfile.ZipFile(package) as z:file.write_bytes(z.read('ref/'+tfm+'/System.Runtime.CompilerServices.Unsafe.dll'))
 run('reference-'+tfm,[dotnet,native(checker),native(file),native(here/'inputs'/('reference-'+tfm+'.json')),'--reference',native(here/'inputs/version-policy.json')])
if package:
 bridge=out/'consumer';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
 (bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><AllowUnsafeBlocks>true</AllowUnsafeBlocks><LangVersion>7.3</LangVersion><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Runtime.CompilerServices.Unsafe" Version="[4.5.2]"/></ItemGroup></Project>\n')
 run('consumer-build',[dotnet,'build',native(bridge/'Bridge.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 assert (out/'cache/system.runtime.compilerservices.unsafe/4.5.2/system.runtime.compilerservices.unsafe.4.5.2.nupkg').read_bytes()==package.read_bytes()
 assets=json.loads((bridge/'obj/project.assets.json').read_text());assert not assets.get('logs')
 assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0','System.Runtime.CompilerServices.Unsafe/4.5.2'}
 selected=assets['targets']['.NETStandard,Version=v2.0']['System.Runtime.CompilerServices.Unsafe/4.5.2']
 assert set(selected['compile'])=={'ref/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'}
 assert set(selected['runtime'])=={'lib/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'}
 owned=out/'consumer-owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
 with zipfile.ZipFile(package) as z:(owned/'System.Runtime.CompilerServices.Unsafe.dll').write_bytes(z.read('lib/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'))
 run('consumer-run',[dotnet,native(checker),native(owned/'System.Runtime.CompilerServices.Unsafe.dll'),native(here/'inputs/published-netstandard2.0.json'),native(here/'inputs/il-bodies-netstandard2.0.json'),native(here/'inputs/version-policy.json')])
 print((out/'consumer-run.log').read_text(),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_runtime_profiles=['netstandard1.0','netstandard2.0','netcoreapp2.0'],original_reference_profiles=['netstandard1.0','netstandard2.0'],original_public_API_entries_per_profile=35,all_original_public_IL_method_bodies_equal=True,all_34_public_methods_executed_in_each_runtime_profile=True,all_native_VERSIONINFO_fields_equal=True,isolated_exact_old_implementation_executed=True,source_NET8_execution_host=True,fresh_NS2_PackageReference_consumer_passed=package is not None,exact_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest() if package else None,full_historical_runtime_matrix_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
