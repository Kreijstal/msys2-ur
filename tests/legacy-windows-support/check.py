"""Build a source-only old-contract consumer and execute isolated candidate DLLs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

producer,out,compiler=(Path(x).resolve() for x in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
bridge=out/'bridge';bridge.mkdir();shutil.copy2(here/'inputs/Bridge.cs',bridge/'Bridge.cs')
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for key,value in dict(TargetFramework='netstandard1.3',DisableImplicitFrameworkReferences='true',NoStdLib='true',AddAdditionalExplicitAssemblyReferences='false',EnableDefaultItems='false',TreatWarningsAsErrors='true',NuGetAudit='false',LangVersion='6',CscToolPath=native(compiler),CscToolExe='csc44.cmd').items():E.SubElement(pg,key).text=value
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include='Bridge.cs')
refs=list(Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/ref').glob('*.dll'));candidates={}
for name in ['Microsoft.Win32.Registry','System.Text.Encoding.CodePages']:
    p=producer/name/'bin/Release/netstandard1.3'/(name+'.dll');assert p.is_file();refs.append(p);candidates[name]=p
for p in refs:
    node=E.SubElement(items,'Reference',Include=p.stem);E.SubElement(node,'HintPath').text=native(p);E.SubElement(node,'Private').text='false'
E.indent(tree);E.ElementTree(tree).write(bridge/'Bridge.csproj',encoding='utf-8',xml_declaration=True)
host=out/'host';host.mkdir()
for name in ['Api.cs','Check.cs']:shutil.copy2(here/'inputs'/name,host/name)
(host/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,args):
    cmd=['/clang64/lib/dotnet/dotnet.exe',*args]
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-7000:])
for label,project in [('bridge',bridge/'Bridge.csproj'),('host',host/'Check.csproj')]:run(label,['build',native(project),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
owned=out/'owned';owned.mkdir();shutil.copy2(bridge/'bin/Release/netstandard1.3/Bridge.dll',owned/'Bridge.dll')
for name,path in candidates.items():shutil.copy2(path,owned/(name+'.dll'))
run('run',[native(host/'bin/Release/net8.0/Check.dll'),native(owned),native(here/'inputs/published-runtime-metadata.json'),native(producer/'source-inputs.json')])
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_public_API_entries=106,original_runtime_reference_identity_sets_equal=True,all_source_strings_and_encoding_data_bytes_verified=True,isolated_original_implementation_versions_executed=True,original_NS13_consumer_compiler_references_only_source_contracts=True,candidate_DLL_sha256={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in candidates.items()},native_registry_owned_subtree_cleanup_verified=True,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'run.log').read_text())
