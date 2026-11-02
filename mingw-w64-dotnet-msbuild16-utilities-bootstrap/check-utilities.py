"""Fresh original NS2 PackageReference consumer with isolated runtime libraries."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import argparse

parser=argparse.ArgumentParser();parser.add_argument('producer',type=Path);parser.add_argument('out',type=Path);parser.add_argument('feed',type=Path,nargs='?');parser.add_argument('--legacy-feed',type=Path);options=parser.parse_args()
producer,out=options.producer.resolve(),options.out.resolve();assert not out.exists();out.mkdir();here=Path(__file__).parent
feed=options.feed.resolve() if options.feed else producer/'feed';native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
candidate=options.legacy_feed or Path('/clang64/lib/dotnet/library-packs')
origins=[('utilities',native(feed)),('legacy',native(candidate)),('source',native(Path('/clang64/lib/dotnet/library-packs')))];unique={};keys={}
for key,path in origins:unique.setdefault(path,key);keys[key]=unique[path]
patterns={key:[] for key in unique.values()}
for key,pattern in [('utilities','Microsoft.Build.Utilities.Core'),('legacy','Microsoft.Win32.Registry'),('legacy','System.Text.Encoding.CodePages'),('source','*')]:patterns[keys[key]].append(pattern)
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="'+key+'" value="'+path+'"/>' for path,key in unique.items())+'</packageSources><packageSourceMapping>'+''.join('<packageSource key="'+key+'">'+''.join('<package pattern="'+p+'"/>' for p in values)+'</packageSource>' for key,values in patterns.items())+'</packageSourceMapping></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
bridge=out/'bridge';bridge.mkdir();shutil.copy2(here/'inputs/UtilitiesBridge.cs',bridge/'Bridge.cs')
(bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><LangVersion>7.3</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Build.Utilities.Core" Version="[16.0.461]"/></ItemGroup></Project>\n')
host=out/'host';host.mkdir();shutil.copy2(here/'inputs/Api.cs',host/'Api.cs');shutil.copy2(here/'inputs/UtilitiesCheck.cs',host/'Check.cs')
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,args):
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-6500:])
for label,project in [('bridge',bridge/'Bridge.csproj'),('host',host/'Check.csproj')]:run(label,['build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
owned=out/'owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll');payload={}
for name,version in [('Microsoft.Build.Utilities.Core','16.0.461'),('Microsoft.Build.Framework','16.0.461'),('System.Collections.Immutable','1.5.0'),('Microsoft.Win32.Registry','4.3.0'),('System.Text.Encoding.CodePages','4.0.1')]:
    package=out/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg')
    if name=='Microsoft.Build.Utilities.Core':
        original=next(p for p in feed.glob('*.nupkg') if p.name.lower()==name.lower()+'.'+version+'.nupkg');assert package.read_bytes()==original.read_bytes()
    with zipfile.ZipFile(package) as z:data=z.read('lib/netstandard2.0/'+name+'.dll')
    (owned/(name+'.dll')).write_bytes(data);payload[name]=hashlib.sha256(data).hexdigest()
for assets in [bridge/'obj/project.assets.json',host/'obj/project.assets.json']:assert not json.loads(assets.read_text()).get('logs')
run('run',[native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/utilities16-published-metadata.json'),native(producer/'producer-audit.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=487,original_runtime_dependency_identity_sets_equal=True,source_resource_strings_verified=110,original_NS2_PackageReference_consumer=True,exact_cached_candidate_NuGet_archive_verified=True,formal_pacman_installed=options.feed is not None,isolated_original_implementations_executed=True,consumer_DLL_sha256=payload,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'run.log').read_text())
