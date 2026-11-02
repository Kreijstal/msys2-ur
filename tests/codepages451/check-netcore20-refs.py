"""Check the selected NETCore2.0 source contract graph without executing refs."""
from pathlib import Path
import functools,json,os,shutil,subprocess,sys
producer,out=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
for n,target in [('ReferenceCheck.cs','Program.cs'),('Api.cs','Api.cs')]:shutil.copy2(here/'inputs'/n,out/target)
(out/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe';commands=[]
for label,cmd in [('build',[dotnet,'build',native(out/'Check.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']),('metadata',[dotnet,native(out/'bin/Release/net8.0/Check.dll'),native(producer/'ref'),native(here/'inputs/netcore20-published-metadata.json')])]:
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_API_entries=sum(len(v['api']) for v in json.loads((here/'inputs/netcore20-published-metadata.json').read_text()).values()),original_reference_identity_dependencies_and_API_verified=True,published_DLL_executed_or_used_as_compiler_reference=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'metadata.log').read_text())
