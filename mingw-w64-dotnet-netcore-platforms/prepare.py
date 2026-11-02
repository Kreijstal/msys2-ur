"""Package the upstream 1.1.2 runtime graph without building legacy corefx."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
folder=source/'pkg/Microsoft.NETCore.Platforms'
original=E.parse(folder/'Microsoft.NETCore.Platforms.pkgproj').getroot()
assert original.findtext('.//{*}PackageVersion')=='1.1.2'
graph=(folder/'runtime.json').read_bytes()
assert hashlib.sha256(graph).hexdigest()=='2738181f98f68ee46bb401ff9ded2f7eec03e1d517004337607dcbdfdb1b99f1'
assert len(json.loads(graph)['runtimes'])==165
(out/'runtime.json').write_bytes(graph)
(out/'_._').write_bytes(b'')
(out/'LICENSE').write_bytes((source/'LICENSE').read_bytes())
(out/'THIRD-PARTY-NOTICES').write_bytes((source/'THIRD-PARTY-NOTICES').read_bytes())
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out/'Graph.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><IncludeBuildOutput>false</IncludeBuildOutput><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NuspecFile>Graph.nuspec</NuspecFile></PropertyGroup></Project>\n''')
p=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');m=E.SubElement(p,'metadata')
for k,v in dict(id='Microsoft.NETCore.Platforms',version='1.1.2',authors='Microsoft',description='Pinned upstream .NET runtime identifier fallback graph, 165 runtime IDs.').items():E.SubElement(m,k).text=v
E.SubElement(m,'license',type='expression').text='MIT'
E.SubElement(m,'repository',type='git',url='https://github.com/dotnet/corefx',commit='718443a10dbd456b6c8f08ee594a92cfbf2ef8db')
f=E.SubElement(p,'files')
for path,target in [('runtime.json',''),('_._','lib/netstandard1.0/'),('LICENSE',''),('THIRD-PARTY-NOTICES','')]:E.SubElement(f,'file',src=path,target=target or path)
E.indent(p);E.ElementTree(p).write(out/'Graph.nuspec',encoding='utf-8',xml_declaration=True)
