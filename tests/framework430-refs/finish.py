"""Restore only original assembly metadata omitted by reference snapshots."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

producer, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
assert hashlib.sha256(package.read_bytes()).hexdigest() == 'c32254ab0d8d040d0aed45d8b3e521c319fa035041aa029685341b46b167bb30'
with zipfile.ZipFile(package) as z: (out / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
for n,v in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='Restore',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',TreatWarningsAsErrors='true',CscToolPath=(prefix/'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),CscToolExe='csc50.cmd').items(): E.SubElement(pg,n).text=v
items=E.SubElement(tree,'ItemGroup');E.SubElement(items,'Compile',Include=(here/'inputs/RestoreAttributes.cs').as_posix());E.SubElement(items,'Reference',Include='Mono.Cecil',HintPath=(out/'Mono.Cecil.dll').as_posix())
E.indent(tree);E.ElementTree(tree).write(out/'Restore.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands=[];env=dict(os.environ,DOTNET_CLI_HOME=(out/'cli-home').as_posix(),MSBuildEnableWorkloadResolver='false')
for label,cmd in [('build',[prefix/'lib/dotnet/dotnet.exe','build',out/'Restore.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('restore',[prefix/'lib/dotnet/dotnet.exe',out/'bin/Release/net8.0/Restore.dll',here/'inputs',producer/'raw',out/'ref'])]:
 command=[str(p) for p in cmd];r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode('utf-8',errors='replace')[-5000:])
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_Cecil_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),known_original_assembly_attribute_metadata_restored=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original assembly metadata restored for all13 source profiles')
