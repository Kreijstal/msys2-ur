"""Describe NuGet assets using only the source-built outputs."""
from pathlib import Path
import json
import os
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1]).resolve()
folder = root/'packages'
folder.mkdir(exist_ok=True)
relative = lambda p: os.path.relpath(p, folder).replace('\\', '/')
version = '4.10.3'
names = ['System.Private.ServiceModel', 'System.Web.Services.Description'] + [
    'System.ServiceModel.'+name for name in ['Primitives', 'Duplex', 'Security', 'Http', 'NetTcp']]
records = []
for name in names:
    package = ET.Element('package', xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
    metadata = ET.SubElement(package, 'metadata')
    for key, value in dict(id=name, version=version, authors='Microsoft',
            description=name+' built from pinned upstream sources for the offline .NET 8 feed.').items():
        ET.SubElement(metadata, key).text = value
    ET.SubElement(metadata, 'license', type='expression').text = 'MIT'
    ET.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/wcf',
                  commit='6c05fa33450ee3960f0763948e91327f049b302b')
    dependencies = {}
    if name == 'System.Private.ServiceModel':
        dependencies = {'Microsoft.Extensions.ObjectPool': '8.0.31', 'System.Security.Cryptography.Xml': '8.0.4'}
    elif name.startswith('System.ServiceModel.'):
        dependencies = {'System.Private.ServiceModel': version}
        if name.endswith('.Primitives'):
            dependencies['System.ServiceModel.Syndication'] = '8.0.0'
        else:
            dependencies['System.ServiceModel.Primitives'] = version
    group = ET.SubElement(ET.SubElement(metadata, 'dependencies'), 'group', targetFramework='net8.0')
    for dependency, dep_version in dependencies.items():
        ET.SubElement(group, 'dependency', id=dependency, version='['+dep_version+']')
    files = ET.SubElement(package, 'files')
    assets = []
    def asset(source, target):
        assert source.is_file(), source
        ET.SubElement(files, 'file', src=relative(source), target=target)
        assets.append(target.rstrip('/')+'/'+source.name)
    if name in names[:2]:
        binary = root/name/'bin/Release/net8.0'/(name+'.dll')
        asset(binary, 'lib/net8.0/')
        if name == 'System.Private.ServiceModel':
            # Keep Private out of the compile surface; the five source reference
            # contracts provide those types, exactly as in the upstream layout.
            (folder/'_._').write_text('')
            asset(folder/'_._', 'ref/net8.0/')
        else:
            asset(root/name/'obj/Release/net8.0/ref'/(name+'.dll'), 'ref/net8.0/')
        for satellite in sorted(binary.parent.glob('*/'+name+'.resources.dll')):
            asset(satellite, 'lib/net8.0/'+satellite.parent.name+'/')
    else:
        asset(root/'facades'/name/'bin/Release/net8.0'/(name+'.dll'), 'lib/net8.0/')
        asset(root/'contracts'/name/'obj/Release/net8.0/ref'/(name+'.dll'), 'ref/net8.0/')
        if name.endswith('.Primitives'):
            asset(root/'legacy/bin/Release/net8.0/System.ServiceModel.dll', 'lib/net8.0/')
            asset(root/'legacy/obj/Release/net8.0/ref/System.ServiceModel.dll', 'ref/net8.0/')
    ET.indent(package)
    ET.ElementTree(package).write(folder/(name+'.nuspec'), encoding='utf-8', xml_declaration=True)
    records.append({'id': name, 'version': version, 'dependencies': dependencies, 'assets': assets})
(folder/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
props = ET.SubElement(project, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', EnableDefaultItems='false',
        EnableNETAnalyzers='false', NuGetAudit='false', IncludeBuildOutput='false',
        NoPackageAnalysis='false').items():
    ET.SubElement(props, name).text = value
ET.indent(project)
ET.ElementTree(project).write(folder/'pack.csproj', encoding='utf-8', xml_declaration=True)
