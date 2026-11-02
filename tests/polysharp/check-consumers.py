"""Use the original package targets and analyzer through real NuGet consumers."""
from pathlib import Path
import json
import os
import subprocess
import sys

out,check=(Path(p).resolve() for p in sys.argv[1:3]);assert not check.exists();check.mkdir()
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else out/'feed'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
config=check/'NuGet.config'
sources=list(dict.fromkeys([native(feed),native(Path('/clang64/lib/dotnet/library-packs'))]))
config.write_text('<configuration><packageSources><clear/>'+''.join('<add key="source'+str(i)+'" value="'+p+'"/>' for i,p in enumerate(sources))+'</packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
commands=[]
for tfm in ['netstandard2.0','net8.0']:
    folder=check/tfm;folder.mkdir()
    project=folder/'Check.csproj'
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>'+tfm+'</TargetFramework><OutputType>'+('Exe' if tfm=='net8.0' else 'Library')+'</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><LangVersion>13.0</LangVersion><Nullable>enable</Nullable><EmitCompilerGeneratedFiles>true</EmitCompilerGeneratedFiles></PropertyGroup><ItemGroup><PackageReference Include="PolySharp" Version="[1.15.0]"/></ItemGroup></Project>\n')
    (folder/'Program.cs').write_text('''using System;
public record Entry(int Value);
public class RequiredData { public required string Name { get; init; } }
public static class Program {
    public static int Main() {
        var value = new RequiredData { Name = "owned" };
        var bounds = new Range(1, new Index(1, true)).GetOffsetAndLength(5);
        if (new Entry(38).Value + bounds.Offset + bounds.Length != 42) throw new Exception("Polyfill behavior");
        Console.WriteLine("PASS package targets/analyzer generation and records/required members/range behavior");
        return 0;
    }
}
''')
    cmd=['/clang64/lib/dotnet/dotnet.exe','build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-p:CscToolPath='+native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),'-p:CscToolExe=csc50.cmd','-v:minimal']
    with (folder/'build.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    assets=json.loads((folder/'obj/project.assets.json').read_text());assert not assets.get('logs')
    assert 'PolySharp/1.15.0' in assets['libraries']
    assert (check/'cache/polysharp/1.15.0/polysharp.1.15.0.nupkg').read_bytes()==next(p for p in feed.glob('*.nupkg') if p.name.lower()=='polysharp.1.15.0.nupkg').read_bytes()
    generated=list((folder/'obj').rglob('*.g.cs'))
    assert len(generated)>(10 if tfm=='netstandard2.0' else 0),(tfm,len(generated))
    commands.append(dict(command=cmd,exit_code=0,framework=tfm,generated_files=len(generated)))
    if tfm=='net8.0':
        cmd=['/clang64/lib/dotnet/dotnet.exe',native(folder/'bin/Release/net8.0/Check.dll')]
        with (folder/'run.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        commands.append(dict(command=cmd,exit_code=0))
(check/'results.json').write_text(json.dumps(dict(commands=commands,original_package_targets_and_analyzer_used=True,fresh_source_only_cache_bytes_verified=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS fresh original-package NS2 and NET8 consumers, actual analyzer generation and NET8 execution')
