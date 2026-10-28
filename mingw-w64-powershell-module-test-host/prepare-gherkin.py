"""Build every original Gherkin5.1.0 source file for the source Pester4 test tool."""
from pathlib import Path
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as E

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
root=source/'Gherkin'
project=E.Element('Project',Sdk='Microsoft.NET.Sdk')
properties=E.SubElement(project,'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',AssemblyName='Gherkin',RootNamespace='Gherkin',
    Version='5.1.0',AssemblyVersion='5.0.0.0',FileVersion='5.1.0.0',
    InformationalVersion='5.1.0+55ab34d45dcd8249349704335c2aa2f90839fae3',
    EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',
    GenerateAssemblyInfo='true',DefineConstants='$(DefineConstants);NETSTANDARD1_5').items():E.SubElement(properties,name).text=value
items=E.SubElement(project,'ItemGroup')
inventory={}
for path in sorted(root.rglob('*.cs')):
    E.SubElement(items,'Compile',Include=os.path.relpath(path,output).replace('\\','/'))
    inventory[path.relative_to(source).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
E.SubElement(items,'EmbeddedResource',Include=os.path.relpath(root/'gherkin-languages.json',output).replace('\\','/'),LogicalName='Gherkin.gherkin-languages.json')
E.SubElement(items,'PackageReference',Include='Newtonsoft.Json',Version='[13.0.4]')
E.indent(project);E.ElementTree(project).write(output/'Gherkin.csproj',encoding='utf-8',xml_declaration=True)
(output/'source-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
print('Staged all',len(inventory),'original Gherkin C# files; source Newtonsoft.Json13.0.4 replaces the old10.0.3 build reference')
