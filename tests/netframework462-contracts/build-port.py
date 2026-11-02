"""Build frozen declaration-only Framework4.6.2 ports using source tools only."""
from pathlib import Path
import functools,hashlib,json,os,shutil,subprocess,sys
source,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-9000:])
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');dotnet='/clang64/lib/dotnet/dotnet.exe'
run('compile',['/usr/bin/python3',str(here/'build-contracts.py'),str(source),str(out/'compiled'),str(compiler)])
host=out/'metadata-host';host.mkdir();shutil.copy2(here/'inputs/MetadataPort.cs',host/'Program.cs')
(host/'Port.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><CscToolPath>'+native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap'))+'</CscToolPath><CscToolExe>csc50.cmd</CscToolExe></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n');config=host/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
run('metadata-host-build',[dotnet,'build',native(host/'Port.csproj'),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal']);port=host/'bin/Release/net8.0/Port.dll';ref=out/'ref';ref.mkdir()
for name in ['mscorlib','System.Numerics']:
 policy=here/'inputs'/(name+'-metadata-policy.json');run('port-'+name,[dotnet,native(port),'--apply',native(out/'compiled'/(name+'.dll')),native(policy),native(ref/(name+'.dll'))])
 run('metadata-'+name,[dotnet,native(port),'--record',native(ref/(name+'.dll')),native(out/(name+'.metadata.json'))]);assert json.loads(policy.read_text())==json.loads((out/(name+'.metadata.json')).read_text()),name
record=dict(commands=commands,generated_source_sha256={p.name:sha(p) for p in source.glob('*.cs')},policy_sha256={p.name:sha(p) for p in (here/'inputs').iterdir() if p.is_file()},output_sha256={p.name:sha(p) for p in ref.glob('*.dll')},original_declarative_metadata_restored_and_roundtrip_equal=True,public_reference_contract_ports=True,nonpublic_opaque_support_types=['System.Runtime.Remoting.Identity','System.Runtime.Remoting.ServerIdentity'],full_original_private_type_layouts_reconstructed=False,published_DLL_executed_or_used_as_compiler_reference=False,publisher_implementation_method_bodies_copied=False,original_NET462_runtime_execution_verified=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS source-only Framework4.6.2 reference ports; complete original public metadata round-trip')
