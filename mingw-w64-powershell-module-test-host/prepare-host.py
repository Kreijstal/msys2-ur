"""Stage the owned module test host against complete original PowerShell projects."""
from pathlib import Path
import os
import shutil
import sys
import xml.etree.ElementTree as E

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
shutil.copyfile(Path(__file__).resolve().with_name('ModuleHost.cs'), output/'ModuleHost.cs')
project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
properties = E.SubElement(project, 'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',
    EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',
    AssemblyName='SourcePowerShell.ModuleHost').items():
    E.SubElement(properties,name).text=value
items = E.SubElement(project, 'ItemGroup')
E.SubElement(items,'Compile',Include='ModuleHost.cs')
for name in ('Microsoft.PowerShell.Commands.Utility','Microsoft.PowerShell.Commands.Management',
             'Microsoft.Management.Infrastructure.CimCmdlets','Microsoft.PowerShell.ConsoleHost',
             'Microsoft.PowerShell.Commands.Diagnostics','Microsoft.WSMan.Management'):
    path=source/'src'/name/(name+'.csproj')
    assert path.is_file(),path
    E.SubElement(items,'ProjectReference',Include=os.path.relpath(path,output).replace('\\','/'))
E.indent(project)
E.ElementTree(project).write(output/'ModuleHost.csproj',encoding='utf-8',xml_declaration=True)
