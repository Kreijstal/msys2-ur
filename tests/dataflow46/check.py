"""Run both exact old Dataflow implementations, isolated from runtime copies."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
producer,contracts,out,compiler=(Path(s).resolve() for s in sys.argv[1:5]);assert not out.exists();out.mkdir()
assert not sys.argv[5:] or len(sys.argv)==7 and sys.argv[5]=='--feed'
feed=Path(sys.argv[6]).resolve() if len(sys.argv)==7 else None
package=next(p for p in feed.glob('*.nupkg') if p.name.lower()=='system.threading.tasks.dataflow.4.6.0.nupkg') if feed else None
compiler_dll=next((compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file()),None);assert compiler_dll is not None
here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
record=json.loads((producer/'results.json').read_text())
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
config=out/'NuGet.config';feeds=list(dict.fromkeys(([native(feed)] if feed else [])+[native(Path('/clang64/lib/dotnet/library-packs'))]));config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="feed'+str(i)+'" value="'+value+'"/>' for i,value in enumerate(feeds))+'</packageSources></configuration>\n')
host=out/'host';host.mkdir()
for name in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/name,host/name)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-6000:])
dotnet='/clang64/lib/dotnet/dotnet.exe'
run('host-build',[dotnet,'build',native(host/'Check.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
for tfm,profile in record['profiles'].items():
 owned=out/tfm;owned.mkdir()
 if package:
  with zipfile.ZipFile(package) as z:(owned/'System.Threading.Tasks.Dataflow.dll').write_bytes(z.read('lib/'+tfm+'/System.Threading.Tasks.Dataflow.dll'))
 else:shutil.copy2(producer/tfm/'bin/Release'/tfm/'System.Threading.Tasks.Dataflow.dll',owned/'System.Threading.Tasks.Dataflow.dll')
 refs=[contracts/k/(k.split('/')[0]+'.dll') for k in sorted(profile['reference_sha256'])]
 args=['/nostdlib+','/target:library','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(owned/'Bridge.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[owned/'System.Threading.Tasks.Dataflow.dll']]+['"'+native(here/'inputs/Bridge.cs')+'"']
 rsp=owned/'bridge.rsp';rsp.write_text('\n'.join(args)+'\n')
 run(tfm+'-compile',[dotnet,native(compiler_dll),'-noconfig','@'+native(rsp)])
 run(tfm+'-run',[dotnet,native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs'/('original-dataflow-'+tfm+'.json')),native(producer/'results.json'),tfm])
 print((out/(tfm+'-run.log')).read_text(),flush=True)
if package:
 bridge=out/'ns2-bridge';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
 (bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.Threading.Tasks.Dataflow" Version="[4.6.0]"/></ItemGroup></Project>\n')
 run('ns2-build',[dotnet,'build',native(bridge/'Bridge.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
 assert (out/'cache/system.threading.tasks.dataflow/4.6.0/system.threading.tasks.dataflow.4.6.0.nupkg').read_bytes()==package.read_bytes()
 assets=json.loads((bridge/'obj/project.assets.json').read_text());assert not assets.get('logs')
 assert set(assets['libraries'])=={'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0','System.Threading.Tasks.Dataflow/4.6.0'}
 assert set(assets['targets']['.NETStandard,Version=v2.0']['System.Threading.Tasks.Dataflow/4.6.0']['compile'])=={'lib/netstandard2.0/System.Threading.Tasks.Dataflow.dll'}
 owned=out/'ns2-owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
 with zipfile.ZipFile(package) as z:
  data=z.read('lib/netstandard2.0/System.Threading.Tasks.Dataflow.dll');assert data==z.read('lib/netstandard1.1/System.Threading.Tasks.Dataflow.dll');(owned/'System.Threading.Tasks.Dataflow.dll').write_bytes(data)
 run('ns2-run',[dotnet,native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/original-dataflow-netstandard1.1.json'),native(producer/'results.json'),'netstandard1.1'])
 print((out/'ns2-run.log').read_text(),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_profiles=['netstandard1.0','netstandard1.1'],original_public_API_entries_per_profile=269,original_dependency_identities_equal=True,all_original_source_resource_values_verified=True,isolated_exact_old_implementations_executed=True,ordering_backpressure_batch_join_broadcast_write_once_cancellation_fault_checks_passed=True,source_NET8_execution_host=True,fresh_NS2_PackageReference_consumer_passed=package is not None,NS2_compatibility_DLL_bytes_identical_to_original_NS11=package is not None,exact_nupkg_sha256=hashlib.sha256(package.read_bytes()).hexdigest() if package else None,formal_package_built=False,full_upstream_suite_run=False,historical_runtime_matrix_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
