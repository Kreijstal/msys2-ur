from pathlib import Path
import json,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]);folder=root/'System.Composition';folder.mkdir()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',PackageId='System.Composition',Version='8.0.0',IncludeBuildOutput='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',NoWarn='NU5128',PackageLicenseExpression='MIT',PackageReadmeFile='README.md',Description='MEF2 dependency package built from .NET 8.0.31 sources.').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
E.SubElement(items,'None',Include='../README.md',Pack='true',PackagePath='/')
for lib in json.loads((Path(__file__).parent/'libraries.json').read_text()):
 if lib['id'].startswith('System.Composition.'):
  E.SubElement(items,'PackageReference',Include=lib['id'],Version='[8.0.0]')
(folder/'_._').write_bytes(b'')
E.SubElement(items,'None',Include='_._',Pack='true',PackagePath='lib/net8.0/')
E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
