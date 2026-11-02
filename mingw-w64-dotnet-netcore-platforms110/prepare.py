"""Package the upstream 1.1.0 runtime graph without building legacy corefx."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
folder=source/'pkg/Microsoft.NETCore.Platforms'
original=E.parse(folder/'Microsoft.NETCore.Platforms.pkgproj').getroot()
assert original.findtext('.//{*}PackageVersion')=='1.1.0'
graph=(folder/'runtime.json').read_bytes()
assert hashlib.sha256(graph).hexdigest()=='c011616db5f69bc2e5371641502313d78c0bd38491d2379a609c6970b7eb2595'
assert len(json.loads(graph)['runtimes'])==117
(out/'runtime.json').write_bytes(graph)
(out/'_._').write_bytes(b'')
(out/'LICENSE').write_bytes((source/'LICENSE').read_bytes())
(out/'THIRD-PARTY-NOTICES').write_bytes((source/'THIRD-PARTY-NOTICES').read_bytes())
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out/'Graph.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><IncludeBuildOutput>false</IncludeBuildOutput><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><NuspecFile>Graph.nuspec</NuspecFile></PropertyGroup></Project>\n''')
p=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');m=E.SubElement(p,'metadata')
for k,v in dict(id='Microsoft.NETCore.Platforms',version='1.1.0',authors='Microsoft',description='Pinned upstream .NET runtime identifier fallback graph, 117 runtime IDs.').items():E.SubElement(m,k).text=v
E.SubElement(m,'license',type='expression').text='MIT'
E.SubElement(m,'repository',type='git',url='https://github.com/dotnet/corefx',commit='8808e3e7f9749a168f86180496d6ea0f8e159db2')
f=E.SubElement(p,'files')
for path,target in [('runtime.json',''),('_._','lib/netstandard1.0/'),('LICENSE',''),('THIRD-PARTY-NOTICES','')]:E.SubElement(f,'file',src=path,target=target or path)
E.indent(p);E.ElementTree(p).write(out/'Graph.nuspec',encoding='utf-8',xml_declaration=True)
