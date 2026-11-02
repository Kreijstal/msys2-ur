"""Execute original facade forwards and owned Counter/socket implementations."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

producer,out,prefix=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='RunFacades',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items():E.SubElement(pg,n).text=v
E.SubElement(E.SubElement(t,'ItemGroup'),'Compile',Include=(here/'inputs/RunFacades.cs').as_posix());E.indent(t);E.ElementTree(t).write(out/'RunFacades.csproj',encoding='utf-8',xml_declaration=True);(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
dotnet=prefix/'lib/dotnet/dotnet.exe';commands=[];env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),MSBuildEnableWorkloadResolver='false')
for label,args in [('build',[dotnet,'build',out/'RunFacades.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('run',[dotnet,out/'bin/Release/net8.0/RunFacades.dll',producer,here/'inputs/profiles.json',here/'inputs/baselines1'])]:
    command=[str(p) for p in args];r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:]);print(r.stdout.decode(errors='replace'),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,all_94_original_exported_types_resolved_to_source_NET8=True,original_source_EventCounter_statistics_executed=True,all_13_original_source_SocketTaskExtensions_overloads_executed=True,owned_TCP_UDP_payload_and_packet_metadata_verified=True,original_Framework_runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
