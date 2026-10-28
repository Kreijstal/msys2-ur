"""Generate the historical method-free forwarding shim from audited API data."""
from pathlib import Path
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

root, syndication = (Path(x).resolve() for x in sys.argv[1:])
inputs = Path(__file__).resolve().parent
metadata = json.loads((inputs/'legacy-forwards.json').read_text())
assert metadata['method_definitions'] == 0
assert len(metadata['forwards']) == 274
folder = root/'legacy'
folder.mkdir(exist_ok=True)
relative = lambda p: os.path.relpath(p, folder).replace('\\', '/')
key = bytes.fromhex('00000000000000000400000000000000')
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == 'b77a5c561934e089'
(folder/'ECMA.public.snk').write_bytes(key)
code = []
for entry in metadata['forwards']:
    name = entry['type']
    if '+' in name:
        continue  # C# emits nested forwards with their containing type.
    if '`' in name:
        name, arity = name.split('`')
        name += '<' + ','*(int(arity)-1) + '>'
    code.append('[assembly: System.Runtime.CompilerServices.TypeForwardedTo(typeof(global::'+name+'))]')
assert len(code) == 270
(folder/'Forwards.cs').write_text('\n'.join(code)+'\n')
project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
props = ET.SubElement(project, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', AssemblyName='System.ServiceModel',
        Version='4.10.3', AssemblyVersion='4.0.0.0', FileVersion='4.10.3.0',
        InformationalVersion='4.10.3+6c05fa33450ee3960f0763948e91327f049b302b',
        IncludeSourceRevisionInInformationalVersion='false', EnableDefaultItems='false',
        EnableNETAnalyzers='false', NuGetAudit='false', SignAssembly='true', PublicSign='true',
        AssemblyOriginatorKeyFile='ECMA.public.snk', ProduceReferenceAssembly='true').items():
    ET.SubElement(props, name).text = value
items = ET.SubElement(project, 'ItemGroup')
ET.SubElement(items, 'Compile', Include='Forwards.cs')
for target in sorted({entry['target'] for entry in metadata['forwards']}):
    path = (syndication if target == 'System.ServiceModel.Syndication' else
            root/'contracts'/target/'obj/Release/net8.0/ref'/(target+'.dll'))
    assert path.is_file(), path
    reference = ET.SubElement(items, 'Reference', Include=target)
    ET.SubElement(reference, 'HintPath').text = relative(path)
    ET.SubElement(reference, 'Private').text = 'false'
ET.indent(project)
ET.ElementTree(project).write(folder/'build.csproj', encoding='utf-8', xml_declaration=True)
