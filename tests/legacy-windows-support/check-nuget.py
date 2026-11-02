"""Restore the NS2 compatibility profile from source archives and run original DLLs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

producer,out=(Path(x).resolve() for x in sys.argv[1:3]);assert not out.exists();out.mkdir()
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else producer/'feed';here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
paths=list(dict.fromkeys([native(feed),native(Path('/clang64/lib/dotnet/library-packs'))]));config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="source'+str(i)+'" value="'+p+'"/>' for i,p in enumerate(paths))+'</packageSources></configuration>\n')
bridge=out/'bridge';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
(bridge/'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><LangVersion>6</LangVersion></PropertyGroup><ItemGroup><Compile Include="Bridge.cs"/><PackageReference Include="Microsoft.Win32.Registry" Version="[4.3.0]"/><PackageReference Include="System.Text.Encoding.CodePages" Version="[4.0.1]"/></ItemGroup></Project>\n')
host=out/'host';host.mkdir()
for name in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/name,host/name)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,args):
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-7000:])
for label,project in [('bridge',bridge/'Bridge.csproj'),('host',host/'Check.csproj')]:run(label,['build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
owned=out/'owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard2.0/Bridge.dll',owned/'Bridge.dll');payload={};reference_owned=out/'owned-references';reference_owned.mkdir()
for name,version in [('Microsoft.Win32.Registry','4.3.0'),('System.Text.Encoding.CodePages','4.0.1')]:
    filename=name.lower()+'.'+version+'.nupkg';package=next(p for p in feed.glob('*.nupkg') if p.name.lower()==filename)
    assert (out/'cache'/name.lower()/version/filename).read_bytes()==package.read_bytes()
    with zipfile.ZipFile(package) as z:
        data=z.read('lib/netstandard2.0/'+name+'.dll');assert data==z.read('lib/netstandard1.3/'+name+'.dll')
        reference=z.read('ref/netstandard2.0/'+name+'.dll');assert reference==z.read('ref/netstandard1.3/'+name+'.dll')
        assert (out/'cache'/name.lower()/version/'ref/netstandard2.0'/(name+'.dll')).read_bytes()==reference
        (reference_owned/(name+'.dll')).write_bytes(reference)
    (owned/(name+'.dll')).write_bytes(data);payload[name]=hashlib.sha256(data).hexdigest()
assets=json.loads((bridge/'obj/project.assets.json').read_text());assert not assets.get('logs');assert set(assets['libraries'])=={'Microsoft.Win32.Registry/4.3.0','System.Text.Encoding.CodePages/4.0.1','NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.0'},set(assets['libraries'])
target=assets['targets']['.NETStandard,Version=v2.0']
for name,version in [('Microsoft.Win32.Registry','4.3.0'),('System.Text.Encoding.CodePages','4.0.1')]:assert set(target[name+'/'+version]['compile'])=={'ref/netstandard2.0/'+name+'.dll'}
run('run',[native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/published-runtime-metadata.json'),native(producer/'source-inputs.json'),native(reference_owned),native(here/'inputs/published-reference-metadata.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=106,original_reference_API_entries=102,original_reference_identity_sets_equal=True,original_runtime_reference_identity_sets_equal=True,original_NS13_DLL_bytes_identical_to_NS2_compatibility_assets=True,all_source_strings_and_encoding_data_bytes_verified=True,fresh_NS2_PackageReference_consumer_zero_restore_diagnostics=True,NS2_base_contract='NETStandard.Library/2.0.3',isolated_original_implementations_executed=True,DLL_sha256=payload,formal_pacman_installed=len(sys.argv)==4,original_NS13_NuGet_runtime_closure_verified=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'run.log').read_text())
