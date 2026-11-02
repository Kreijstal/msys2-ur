"""Execute the produced generator on the exact source-built Roslyn4.3 host."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

out, check = (Path(p).resolve() for p in sys.argv[1:3])
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else out/'feed'
assert not check.exists();check.mkdir()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
assembly=out/'source/src/PolySharp.SourceGenerators/bin/Release/netstandard2.0/PolySharp.SourceGenerators.dll'
with zipfile.ZipFile(next(p for p in feed.glob('*.nupkg') if p.name.lower()=='polysharp.1.15.0.nupkg')) as z:
    if len(sys.argv)!=4:assert z.read('analyzers/dotnet/cs/PolySharp.SourceGenerators.dll')==assembly.read_bytes()
    (check/'PolySharp.SourceGenerators.dll').write_bytes(z.read('analyzers/dotnet/cs/PolySharp.SourceGenerators.dll'))
inputs=json.loads((out/'source-inputs.json').read_text())
prefix='src/PolySharp.SourceGenerators/'
resources={'PolySharp.SourceGenerators.'+rel.removeprefix(prefix).replace('/','.'):digest for rel,digest in inputs['original_file_sha256'].items() if rel.startswith(prefix+'EmbeddedResources/') and rel.endswith('.cs')}
assert len(resources)==56
(check/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
(check/'Check.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><EnableNETAnalyzers>false</EnableNETAnalyzers><LangVersion>13.0</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="[4.3.1]"/><Reference Include="PolySharp.SourceGenerators"><HintPath>PolySharp.SourceGenerators.dll</HintPath></Reference></ItemGroup></Project>\n''')
(check/'Program.cs').write_bytes((Path(__file__).parent/'inputs/Check.cs').read_bytes())
(check/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
command=['/clang64/lib/dotnet/dotnet.exe','build',native(check/'Check.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-p:CscToolPath='+native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),'-p:CscToolExe=csc50.cmd','-v:minimal']
with (check/'build.log').open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
run=['/clang64/lib/dotnet/dotnet.exe',native(check/'bin/Release/net8.0/Check.dll'),native(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0')),native(check/'resources.json')]
with (check/'run.log').open('w') as log:result=subprocess.run(run,env=env,stdout=log,stderr=subprocess.STDOUT)
(check/'results.json').write_text(json.dumps(dict(build_command=command,run_command=run,exit_code=result.returncode,exact_Roslyn431_host=True,full_dependency_goal_complete=False),indent=2)+'\n')
print((check/'run.log').read_text())
assert result.returncode==0
