"""Check the selected NETCore2.0 source contract graph without executing refs."""
from pathlib import Path
import functools,json,os,shutil,subprocess,sys
producer,out,compiler=(Path(s).resolve() for s in sys.argv[1:4]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
for n,target in [('ReferenceCheck.cs','Program.cs'),('Api.cs','Api.cs')]:shutil.copy2(here/'inputs'/n,out/target)
(out/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
for label,cmd in [('build',[dotnet,'build',native(out/'Check.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']),('metadata',[dotnet,native(out/'bin/Release/net8.0/Check.dll'),native(producer/'ref'),native(here/'inputs/netcore20-published-metadata.json')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')
# Independently validate the installed/generated forwarding table.
facade=out/'facade-check';facade.mkdir();shutil.copy2(here/'inputs/FacadePort.cs',facade/'Program.cs');(facade/'Port.csproj').write_text((out/'Check.csproj').read_text())
run_commands=[('facade-host-build',[dotnet,'build',native(facade/'Port.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']),('facade-metadata',[dotnet,native(facade/'bin/Release/net8.0/Port.dll'),'--check',native(here/'inputs/netstandard20-forwarders.json'),native(here/'inputs/netstandard20-facade-published.json'),native(producer/'ref/netstandard.dll')])]
# The project filename controls the output assembly name.
for label,cmd in run_commands:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')
import zipfile,hashlib
shutil.copy2(here/'inputs/Probe.cs',out/'Probe.cs');driver=next(compiler/n for n in ['csc.dll','CompilerHost.dll'] if (compiler/n).is_file())
package=Path('/clang64/lib/dotnet/library-packs/system.runtime.compilerservices.unsafe.4.5.2.nupkg');reference=out/'Unsafe.source-reference.dll'
with zipfile.ZipFile(package) as z:reference.write_bytes(z.read('ref/netstandard2.0/System.Runtime.CompilerServices.Unsafe.dll'))
refs=sorted((producer/'ref').glob('*.dll'));assert len(refs)==10
rsp=out/'probe.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/unsafe+','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/out:"'+native(out/'Probe.dll')+'"']+['/reference:"'+native(f)+'"' for f in refs+[reference]]+['"'+native(out/'Probe.cs')+'"'])+'\n')
(out/'Probe.runtimeconfig.json').write_text('{"runtimeOptions":{"tfm":"net8.0","framework":{"name":"Microsoft.NETCore.App","version":"8.0.31"}}}\n')
for label,cmd in [('probe-build',[dotnet,native(driver),'-noconfig','@'+native(rsp)]),('probe-run',[dotnet,native(out/'Probe.dll')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_API_entries=sum(len(v['api']) for v in json.loads((here/'inputs/netcore20-published-metadata.json').read_text()).values()),original_reference_identity_dependencies_and_API_verified=True,original_facade_2417_forwarders_86_scopes_verified=True,typed_consumer_only_source_references_and_original_Unsafe_NS2_reference_compiled=True,typed_consumer_source_NET8_runtime_passed=True,original_NETCore2_runtime_execution_verified=False,published_DLL_executed_or_used_as_compiler_reference=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'metadata.log').read_text());print((out/'facade-metadata.log').read_text());print((out/'probe-run.log').read_text())
