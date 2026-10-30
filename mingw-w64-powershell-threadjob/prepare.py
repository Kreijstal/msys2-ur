"""Stage the complete original ThreadJob sources against source PowerShell7.4."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

source,output=(Path(p).resolve() for p in sys.argv[1:])
golden=json.loads(Path(__file__).resolve().with_name('published-provenance.json').read_text())
output.mkdir()
root=source/'PSThreadJob'
overlay=output/'overlays';overlay.mkdir()
main=overlay/'PSThreadJob.cs';main.write_text((root/main.name).read_text(encoding='utf-8-sig'))
patch=Path(__file__).resolve().with_name('0001-use-current-debugger-setbreakpoints-overload.patch')
subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=overlay,check=True)
project=E.Element('Project',Sdk='Microsoft.NET.Sdk')
props=E.SubElement(project,'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',OutputType='Library',RootNamespace='ThreadJob',
    AssemblyName='Microsoft.PowerShell.ThreadJob',AssemblyVersion='2.0.1.0',FileVersion='2.0.1',
    InformationalVersion='2.0.1',IncludeSourceRevisionInInformationalVersion='false',
    EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',
    GenerateAssemblyDescriptionAttribute='false',GenerateAssemblyCopyrightAttribute='false',
    GenerateAssemblyTrademarkAttribute='false').items():E.SubElement(props,name).text=value
items=E.SubElement(project,'ItemGroup');inventory={}
for path in sorted(root.glob('*.cs')):
    compile_path=main if path.name==main.name else path
    E.SubElement(items,'Compile',Include=os.path.relpath(compile_path,output).replace('\\','/'))
    inventory[path.relative_to(source).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
assert len(inventory)==3
assert inventory==golden['source_files']
assert hashlib.sha256((root/'Resources.resx').read_bytes()).hexdigest()==golden['resource_sha256']
assert hashlib.sha256((root/'ThreadJob.psd1').read_bytes()).hexdigest()==golden['source_manifest_sha256']
E.SubElement(items,'EmbeddedResource',Include=os.path.relpath(root/'Resources.resx',output).replace('\\','/'),LogicalName='ThreadJob.Resources.resources')
reference=E.SubElement(items,'Reference',Include='System.Management.Automation')
# Relative MSYS paths are not valid inside native MSBuild; convert the single
# installed source reference to its native path, with no vendor GAC reference.
native=subprocess.check_output(['cygpath','-am',os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll'],text=True).strip()
E.SubElement(reference,'HintPath').text=native
E.SubElement(reference,'Private').text='false'
E.indent(project);E.ElementTree(project).write(output/'ThreadJob.csproj',encoding='utf-8',xml_declaration=True)
shutil.copyfile(root/'ThreadJob.psd1',output/'ThreadJob.psd1')
shutil.copyfile(source/'LICENSE',output/'LICENSE')
(output/'source-inventory.json').write_text(json.dumps(dict(source_commit='99bfe5adc30ed066973114ea18d7c5091197ee14',
    source_files=inventory,resource_sha256=hashlib.sha256((root/'Resources.resx').read_bytes()).hexdigest(),
    source_algorithm_overlays=[dict(path='PSThreadJob/PSThreadJob.cs',patch=patch.name,
        patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),overlay_sha256=hashlib.sha256(main.read_bytes()).hexdigest(),
        change='Forward SetBreakpoints through the current virtual overload with optional runspace identity')],target_framework='net8.0',source_engine_reference='System.Management.Automation7.4.6.500',
    omitted_build_references=['Windows PowerShell GAC','PowerShellStandard.Library5.1.0-*','Microsoft.CSharp4.5.0-*'],
    replacement='Installed complete source PowerShell7.4.20 engine and inbox.NET8 CSharp binder'),indent=2)+'\n')
