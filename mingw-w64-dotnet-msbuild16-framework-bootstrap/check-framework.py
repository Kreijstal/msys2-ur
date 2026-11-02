"""Check the NS2 candidate's complete API inventory and runtime behavior."""
from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile

producer,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir()
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else producer/'feed'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
here=Path(__file__).parent
(out/'Program.cs').write_bytes((here/'inputs/FrameworkCheck.cs').read_bytes())
(out/'Api.cs').write_bytes((here/'inputs/Api.cs').read_bytes())
(out/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><Nullable>enable</Nullable><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><Compile Include="Api.cs"/><PackageReference Include="Microsoft.Build.Framework" Version="[16.0.461]"/><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
sources=list(dict.fromkeys([native(feed),native(Path('/clang64/lib/dotnet/library-packs'))]))
(out/'NuGet.config').write_text('<configuration><packageSources><clear/>'+''.join('<add key="source'+str(i)+'" value="'+p+'"/>' for i,p in enumerate(sources))+'</packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
commands=[]
for label,args in [('build',['build',native(out/'Check.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']),('run',[native(out/'bin/Release/net8.0/Check.dll'),native(here/'inputs/framework16-published-api.json')])]:
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=result.returncode));assert result.returncode==0,(label,(out/(label+'.log')).read_text()[-4000:])
standard=out/'standard';standard.mkdir()
(standard/'Probe.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Build.Framework" Version="[16.0.461]"/></ItemGroup></Project>\n')
(standard/'Probe.cs').write_text('using Microsoft.Build.Framework; public static class ContractProbe {public static IBuildEngine Engine(ITask task) => task.BuildEngine;public static BuildEventContext Context() => new BuildEventContext(1,2,3,4);}\n')
cmd=['/clang64/lib/dotnet/dotnet.exe','build',native(standard/'Probe.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']
with (out/'standard-build.log').open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
commands.append(dict(command=cmd,exit_code=result.returncode));assert result.returncode==0,(out/'standard-build.log').read_text()
package=next(p for p in feed.glob('*.nupkg') if p.name.lower()=='microsoft.build.framework.16.0.461.nupkg')
assert (out/'cache/microsoft.build.framework/16.0.461/microsoft.build.framework.16.0.461.nupkg').read_bytes()==package.read_bytes()
with zipfile.ZipFile(package) as z:assert (out/'bin/Release/net8.0/Microsoft.Build.Framework.dll').read_bytes()==z.read('lib/netstandard2.0/Microsoft.Build.Framework.dll')
for assets in [out/'obj/project.assets.json',standard/'obj/project.assets.json']:
    assert not json.loads(assets.read_text()).get('logs')
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=743,original_runtime_reference_table_equal=True,source_input_DLL_bytes_verified=True,fresh_NS2_and_NET8_NuGet_consumers=True,formal_pacman_installed=len(sys.argv)==4,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'run.log').read_text())
