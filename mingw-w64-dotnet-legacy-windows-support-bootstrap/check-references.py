"""Validate original compile-time contracts separately from runtime implementations."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

root,out=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
for file in ['Api.cs','ReferenceCheck.cs']:shutil.copy2(here/'inputs'/file,out/file)
(out/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
for label,args in [('build',['build',native(out/'Check.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal']),('run',[native(out/'bin/Release/net8.0/Check.dll'),native(root),native(here/'inputs/published-reference-metadata.json')])]:
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-5500:])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_reference_API_entries=102,Registry_reference_version='4.0.0.0',Registry_implementation_version='4.0.1.0',reference_only=True,source_CSharp_changes=0,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'run.log').read_text())
