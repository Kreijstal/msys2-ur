"""Build the exact .NET 8 type-forwarding source against the source-built inbox."""
from pathlib import Path
import hashlib
import os
import sys
import xml.etree.ElementTree as E

source,output=(Path(x).resolve() for x in sys.argv[1:])
output.mkdir()
inputs=Path(__file__).resolve().parent
library=source/'src/libraries/Microsoft.Bcl.AsyncInterfaces'
upstream=E.parse(library/'src/Microsoft.Bcl.AsyncInterfaces.csproj')
assert upstream.findtext('./PropertyGroup/IsPartialFacadeAssembly')=='true'
forwards=library/'ref/Microsoft.Bcl.AsyncInterfaces.Forwards.cs'
assert forwards.read_text().count('TypeForwardedTo(')==10
key=bytes.fromhex((inputs/'Open.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='cc7b13ffcd2ddd51'
(output/'Open.public.snk').write_bytes(key)
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
values=dict(TargetFramework='net8.0',AssemblyName='Microsoft.Bcl.AsyncInterfaces',
    Version='8.0.0',AssemblyVersion='8.0.0.0',FileVersion='8.0.31.0',
    InformationalVersion='8.0.0+runtime-v8.0.31',IncludeSourceRevisionInInformationalVersion='false',
    EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',
    SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='Open.public.snk',
    PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/runtime',RepositoryType='git',RepositoryBranch='v8.0.31')
for name,value in values.items():E.SubElement(props,name).text=value
E.SubElement(E.SubElement(project,'ItemGroup'),'Compile',Include=os.path.relpath(forwards,output).replace('\\','/'))
E.indent(project);E.ElementTree(project).write(output/'Library.csproj',encoding='utf-8',xml_declaration=True)
(output/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
