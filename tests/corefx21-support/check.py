"""Fresh original-version consumers; isolate them from modern runtime libraries."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

producer,out=(Path(x).resolve() for x in sys.argv[1:3]);assert not out.exists();out.mkdir()
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else producer/'feed'
here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="candidate" value="'+native(feed)+'"/><add key="installed" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
bridge=out/'bridge';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
(bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include="Bridge.cs"/><PackageReference Include="System.Collections.Immutable" Version="[1.5.0]"/><PackageReference Include="System.Reflection.Metadata" Version="[1.6.0]"/></ItemGroup></Project>\n')
host=out/'host';host.mkdir()
for name in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/name,host/name)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,args):
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-6000:])
for label,project in [('bridge',bridge/'Bridge.csproj'),('host',host/'Check.csproj')]:run(label,['build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
owned=out/'owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll')
payload={}
for name,version in [('System.Collections.Immutable','1.5.0'),('System.Reflection.Metadata','1.6.0')]:
    package=next(p for p in feed.glob('*.nupkg') if p.name.lower()==name.lower()+'.'+version+'.nupkg')
    cached=out/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg');assert cached.read_bytes()==package.read_bytes()
    with zipfile.ZipFile(package) as z:data=z.read('lib/netstandard2.0/'+name+'.dll')
    (owned/(name+'.dll')).write_bytes(data);payload[name]=hashlib.sha256(data).hexdigest()
for assets in [bridge/'obj/project.assets.json',host/'obj/project.assets.json']:assert not json.loads(assets.read_text()).get('logs')
run('run',[native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/published-ns2-metadata.json'),native(producer/'source-inputs.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=3874,original_runtime_reference_tables_equal=True,all_source_resource_values_verified=True,isolated_original_version_implementations_executed=True,fresh_original_NS2_PackageReference_consumer=True,exact_cached_archives_and_DLL_bytes=payload,formal_pacman_installed=len(sys.argv)==4,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'run.log').read_text())
