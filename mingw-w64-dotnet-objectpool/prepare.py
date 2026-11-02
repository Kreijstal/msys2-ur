#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
inputs = Path(__file__).resolve().parent
relative = lambda p: os.path.relpath(p, output).replace('\\', '/')
key = bytes.fromhex((inputs / 'AspNetCore.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == 'adb9793829ddae60'
(output / 'Library.public.snk').write_bytes(key)
project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
props = ET.SubElement(project, 'PropertyGroup')
for k,v in dict(TargetFramework='net8.0', AssemblyName='Microsoft.Extensions.ObjectPool',
               RootNamespace='Microsoft.Extensions.ObjectPool', Version='8.0.31', AssemblyVersion='8.0.0.0',
               FileVersion='8.0.31.0', InformationalVersion='8.0.31+aspnetcore-v8.0.31',
               IncludeSourceRevisionInInformationalVersion='false', EnableDefaultItems='false',
               Nullable='enable', EnableNETAnalyzers='false', NuGetAudit='false', SignAssembly='true',
               PublicSign='true', AssemblyOriginatorKeyFile='Library.public.snk', PackageLicenseExpression='MIT',
               RepositoryUrl='https://github.com/dotnet/aspnetcore', RepositoryBranch='v8.0.31',
               ProduceReferenceAssembly='true').items(): ET.SubElement(props,k).text=v
items = ET.SubElement(project, 'ItemGroup')
for path in sorted((source / 'src/ObjectPool/src').glob('*.cs')):
    ET.SubElement(items, 'Compile', Include=relative(path))
for path in ['src/Shared/ThrowHelpers/ArgumentNullThrowHelper.cs', 'src/Shared/CallerArgument/CallerArgumentExpressionAttribute.cs']:
    ET.SubElement(items,'Compile',Include=relative(source/path))
ET.indent(project)
ET.ElementTree(project).write(output/'Library.csproj',encoding='utf-8',xml_declaration=True)
api = source / 'src/ObjectPool/src'
(output/'PublicAPI.txt').write_text((api/'PublicAPI.Shipped.txt').read_text().rstrip()+'\n'+(api/'PublicAPI.Unshipped.txt').read_text().rstrip()+'\n')
(output/'NuGet.config').write_text('<configuration><packageSources><clear /></packageSources></configuration>\n')
