"""Check complete metadata and a consumer built with only source old contracts."""
from pathlib import Path
import json
import hashlib
import os
import shutil
import subprocess
import sys

producer,out,compiler=(Path(x).resolve() for x in sys.argv[1:4]);assert sys.argv[4:] in [[],['--installed']];assert not out.exists();out.mkdir()
here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
compiler_DLL=next((compiler/name for name in ['csc.dll','CompilerHost.dll'] if (compiler/name).is_file()),None);assert compiler_DLL is not None,compiler
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
for name in ['Api.cs','Check.cs','Probe.cs','ProbeDataflow.cs']:shutil.copy2(here/'inputs'/name,out/name)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
(out/'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include="Check.cs"/><Compile Include="Api.cs"/><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands=[]
def run(label,cmd):
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text()[-7000:])
host='/clang64/lib/dotnet/dotnet.exe'
run('check-build',[host,'build',native(out/'Check.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'])
run('metadata',[host,native(out/'bin/Release/net8.0/Check.dll'),native(producer/'ref'),native(here/'inputs/published-metadata.json'),native(here/'inputs/interop-layouts.json'),native(here/'inputs/conditional-attributes.json')])
run('matrix',[host,native(out/'bin/Release/net8.0/Check.dll'),native(producer/'contracts'),native(here/'inputs/published-build-matrix.json'),native(here/'inputs/interop-layouts.json'),native(here/'inputs/conditional-attributes.json')])
args=['/nostdlib+','/target:exe','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/deterministic+','/out:"'+native(out/'Probe.dll')+'"']+['/reference:"'+native(p)+'"' for p in sorted((producer/'ref').glob('*.dll'))]+['"'+native(out/'Probe.cs')+'"']
(out/'probe.rsp').write_text('\n'.join(args)+'\n')
run('probe-build',[host,native(compiler_DLL),'-noconfig','@'+native(out/'probe.rsp')])
run('probe-release-metadata',[host,native(out/'bin/Release/net8.0/Check.dll'),'--verify-release-consumer',native(out/'Probe.dll')])
(out/'Probe.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.31'}}})+'\n')
run('probe-run',[host,native(out/'Probe.dll')])
matrix=json.loads((here/'inputs/published-build-matrix.json').read_text())
dataflow_roots=['System.Collections','System.Collections.Concurrent','System.Diagnostics.Contracts','System.Diagnostics.Debug','System.Diagnostics.Tools','System.Diagnostics.Tracing','System.Dynamic.Runtime','System.Linq','System.Resources.ResourceManager','System.Runtime','System.Runtime.Extensions','System.Runtime.Serialization.Primitives','System.Threading','System.Threading.Tasks']
selected=set()
def select_lower(key):
    if key in selected:return
    assert key in matrix,key
    selected.add(key)
    for reference in matrix[key]['references']:
        name,version=reference.split(', Version=');select_lower(name+'/'+version.split(',')[0])
for name in dataflow_roots:select_lower(name+'/4.0.0.0')
assert all(key.endswith('/4.0.0.0') for key in selected),selected
lower_refs=[producer/'contracts'/key/(key.split('/')[0]+'.dll') for key in sorted(selected)]
args=['/nostdlib+','/target:exe','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/deterministic+','/out:"'+native(out/'ProbeDataflow.dll')+'"']+['/reference:"'+native(p)+'"' for p in lower_refs]+['"'+native(out/'ProbeDataflow.cs')+'"']
(out/'probe-dataflow.rsp').write_text('\n'.join(args)+'\n')
run('probe-dataflow-build',[host,native(compiler_DLL),'-noconfig','@'+native(out/'probe-dataflow.rsp')])
run('probe-dataflow-release-metadata',[host,native(out/'bin/Release/net8.0/Check.dll'),'--verify-release-consumer',native(out/'ProbeDataflow.dll')])
(out/'ProbeDataflow.runtimeconfig.json').write_bytes((out/'Probe.runtimeconfig.json').read_bytes())
run('probe-dataflow-run',[host,native(out/'ProbeDataflow.dll')])
baseline=json.loads((here/'inputs/published-metadata.json').read_text())
matrix=json.loads((here/'inputs/published-build-matrix.json').read_text())
(out/'results.json').write_text(json.dumps(dict(commands=commands,contract_count=len(baseline),build_contract_variant_count=len(matrix),original_public_API_entries=sum(len(v['api']) for v in baseline.values()),build_matrix_original_public_API_entries=sum(len(v['api']) for v in matrix.values()),original_identity_and_dependency_reference_sets_equal=True,original_reference_only_markers=True,original_public_Conditional_attributes_verified=True,public_Conditional_attribute_entries=53,release_Debug_calls_omitted=True,original_COM_struct_layout_and_field_offsets_verified=True,consumer_compiler_references_only_source_legacy_contracts=True,Dataflow_lower_contract_consumer_references={str(p.relative_to(producer/'contracts')):hashlib.sha256(p.read_bytes()).hexdigest() for p in lower_refs},Dataflow_lower_contract_typed_consumer_passed=True,consumer_compiler_DLL_name=compiler_DLL.name,consumer_compiler_DLL_sha256=hashlib.sha256(compiler_DLL.read_bytes()).hexdigest(),consumer_source_NET8_runtime_host=True,formal_pacman_installed=sys.argv[4:]==['--installed'],original_NETCore1x_runtime_matrix_verified=False,CodePages_Diagnostics_Contracts_reference_built=True,CodePages_Diagnostics_Contracts_runtime_package_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'metadata.log').read_text());print('PASS source-only legacy contract consumer compilation and execution on source NET8 host')
