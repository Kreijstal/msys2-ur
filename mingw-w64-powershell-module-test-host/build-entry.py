"""Build unchanged original Windows console entry point for real Start-Job children."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

root,host,out=(Path(p).resolve() for p in sys.argv[1:])
source=root/'PowerShell-7.4.20'
out.mkdir()
original=source/'src/powershell/Program.cs'
shutil.copyfile(original,out/'Program.cs')
project=E.Element('Project',Sdk='Microsoft.NET.Sdk')
props=E.SubElement(project,'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='pwsh',Version='7.4.20',
    InformationalVersion='7.4.20+013edf910bbe781f503c27370941ce54d02d3f33',UseAppHost='true',
    EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items(): E.SubElement(props,name).text=value
items=E.SubElement(project,'ItemGroup');E.SubElement(items,'Compile',Include='Program.cs')
for name in ['System.Management.Automation','Microsoft.PowerShell.ConsoleHost']:
    reference=E.SubElement(items,'Reference',Include=name)
    E.SubElement(reference,'HintPath').text=os.path.relpath(host/(name+'.dll'),out).replace('\\','/')
E.indent(project);E.ElementTree(project).write(out/'Entry.csproj',encoding='utf-8',xml_declaration=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','build',native(out/'Entry.csproj'),'-c','Release',
    '--configfile',native(root/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],check=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
record=dict(original_source='src/powershell/Program.cs',source_sha256=sha(original.read_bytes()),
    source_changes=[],references={name:sha((host/name).read_bytes()) for name in ['System.Management.Automation.dll','Microsoft.PowerShell.ConsoleHost.dll']})
native_host=Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Host.win-x64/8.0.31/runtimes/win-x64/native/apphost.exe')
record['sdk_source_apphost_sha256']=sha(native_host.read_bytes())
record['sdk_source_apphost_path']=str(native_host)
for name in ['pwsh.exe','pwsh.dll','pwsh.runtimeconfig.json']:
    shutil.copyfile(out/'bin/Release/net8.0'/name,host/name)
# Retain the full source host dependency closure; replace only its app entry.
deps=json.loads((host/'SourcePowerShell.ModuleHost.deps.json').read_text())
for target in deps['targets'].values():
    entry=target.pop('SourcePowerShell.ModuleHost/1.0.0')
    entry['runtime']={'pwsh.dll':{}}
    target['pwsh/7.4.20']=entry
deps['libraries']['pwsh/7.4.20']=deps['libraries'].pop('SourcePowerShell.ModuleHost/1.0.0')
(host/'pwsh.deps.json').write_text(json.dumps(deps,indent=2)+'\n')
record['outputs']={name:sha((host/name).read_bytes()) for name in ['pwsh.exe','pwsh.dll','pwsh.runtimeconfig.json','pwsh.deps.json']}
(host/'source-console-entry.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS original console entry source and SDK source apphost staged for real child processes')
