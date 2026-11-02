"""Fresh source-feed consumer and owned IL/nullable/symbol fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

producer,out=(Path(p).resolve() for p in sys.argv[1:3]);assert not out.exists();out.mkdir()
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else producer/'feed'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sources=list(dict.fromkeys([native(feed),native(Path('/clang64/lib/dotnet/library-packs'))]))
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="source'+str(i)+'" value="'+p+'"/>' for i,p in enumerate(sources))+'</packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
commands=[]
def run(label,args):
    command=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=command,exit_code=result.returncode));assert result.returncode==0,(label,(out/(label+'.log')).read_text()[-5000:])
fixture=out/'fixture';fixture.mkdir()
(fixture/'Fixture.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>OwnedFixture</AssemblyName><Nullable>enable</Nullable><DebugType>portable</DebugType><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>\n')
(fixture/'Box.cs').write_text('''namespace Owned;
public class Box {
    public static int Value() => 1;
    public static string? Annotated(string? value) => value;
    public static string Unannotated(string value) => value;
}
''')
consumer=out/'consumer';consumer.mkdir()
(consumer/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><Nullable>enable</Nullable></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
for source in ['Check.cs','Api.cs']:
    (consumer/source).write_bytes((Path(__file__).parent/'inputs'/source).read_bytes())
for name,path in [('fixture',fixture/'Fixture.csproj'),('consumer',consumer/'Check.csproj')]:
    run(name+'-build',['build',native(path),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
    assets=json.loads((path.parent/'obj/project.assets.json').read_text());assert not assets.get('logs'),assets.get('logs')
package=next(p for p in feed.glob('*.nupkg') if p.name.lower()=='mono.cecil.0.11.0.nupkg')
assert (out/'cache/mono.cecil/0.11.0/mono.cecil.0.11.0.nupkg').read_bytes()==package.read_bytes()
with zipfile.ZipFile(package) as z:
    for name in ['Mono.Cecil','Mono.Cecil.Rocks','Mono.Cecil.Mdb','Mono.Cecil.Pdb']:
        assert (consumer/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==z.read('lib/netstandard2.0/'+name+'.dll')
run('runtime',[native(consumer/'bin/Release/net8.0/Check.dll'),native(fixture/'bin/Release/net8.0/OwnedFixture.dll'),native(out/'rewritten'),native(Path(__file__).parent/'inputs/published-ns2-api.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_NS2_four_library_identities=True,actual_IL_and_nullable_metadata_rewriting=True,portable_and_embedded_PDB_round_trips=True,exact_cached_archive_and_copied_DLL_bytes=True,formal_pacman_installed=len(sys.argv)==4,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'runtime.log').read_text(),end='')
