"""Preserve NS1.3 dependency metadata and add byte-identical NS2 compatibility assets."""
from pathlib import Path
import hashlib
import json
import sys
import subprocess
import xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();record=json.loads((root/'source-inputs.json').read_text());contract=json.loads((Path(__file__).parent/'inputs/package-contract.json').read_text())
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
(root/'feed').mkdir()
for name,item in record['libraries'].items():
    folder=root/name;archive=folder/'archive';archive.mkdir();source=folder/'source';dll=folder/'bin/Release/netstandard1.3'/(name+'.dll');assert dll.is_file()
    p=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');metadata=E.SubElement(p,'metadata')
    for k,v in dict(id=name,version=item['version'],authors='Microsoft',description='Windows source build of original '+name+' '+item['version']+' NS1.3. Byte-identical NS2 compatibility assets use source NETStandard.Library2.0.3; original NS1.3 dependency graph remains recorded.').items():E.SubElement(metadata,k).text=v
    E.SubElement(metadata,'license',type='expression').text='MIT'
    E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/corefx',commit=item['source_commit'])
    deps=E.SubElement(metadata,'dependencies');old=E.SubElement(deps,'group',targetFramework='netstandard1.3')
    for dependency in contract[name]['original_NS13_dependencies']:E.SubElement(old,'dependency',**dependency)
    modern=E.SubElement(deps,'group',targetFramework='netstandard2.0');E.SubElement(modern,'dependency',id='NETStandard.Library',version='[2.0.3]')
    files=E.SubElement(p,'files')
    for framework in ['netstandard1.3','netstandard2.0']:E.SubElement(files,'file',src=native(dll),target='lib/'+framework+'/')
    reference=folder/'contract'/(name+'.dll');assert reference.is_file()
    for framework in ['netstandard1.3','netstandard2.0']:E.SubElement(files,'file',src=native(reference),target='ref/'+framework+'/')
    if contract[name]['original_NET46_DLL_identical_to_Windows_NS13']:
        E.SubElement(deps,'group',targetFramework='net46');E.SubElement(files,'file',src=native(dll),target='lib/net46/')
        E.SubElement(files,'file',src=native(dll),target='ref/net46/')
    for license in ['LICENSE','THIRD-PARTY-NOTICES']:
        assert (source/license).is_file();E.SubElement(files,'file',src=native(source/license),target=license)
    port=dict(id=name,version=item['version'],source_commit=item['source_commit'],compiled_original_framework='netstandard1.3',production_CSharp_changes=0,DLL_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),NS2_asset_identical_to_original_NS13_build=True,original_NS13_dependencies=contract[name]['original_NS13_dependencies'],additional_NS2_dependency={'NETStandard.Library':'[2.0.3]'},original_NS13_NuGet_runtime_closure_verified=False,original_NET46_runtime_matrix_verified=False)
    (archive/'source-port.json').write_text(json.dumps(port,indent=2)+'\n');E.SubElement(files,'file',src=native(archive/'source-port.json'),target='source-port.json')
    E.indent(p);E.ElementTree(p).write(archive/'Package.nuspec',encoding='utf-8',xml_declaration=True)
    (archive/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><IncludeBuildOutput>false</IncludeBuildOutput><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n')
print('PASS generated original NS1.3 groups plus explicitly disclosed NS2 compatibility assets')
