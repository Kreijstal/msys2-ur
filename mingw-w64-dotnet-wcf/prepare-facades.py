#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import xml.etree.ElementTree as ET

root=Path(sys.argv[1]).resolve()
for name in ['Primitives','Duplex','Security','Http','NetTcp']:
    assembly='System.ServiceModel.'+name
    folder=root/'facades'/assembly;folder.mkdir(exist_ok=True)
    relative=lambda p:os.path.relpath(p,folder).replace('\\','/')
    project=ET.Element('Project',Sdk='Microsoft.NET.Sdk');props=ET.SubElement(project,'PropertyGroup')
    for k,v in dict(TargetFramework='net8.0',AssemblyName=assembly,Version='4.10.3',AssemblyVersion='4.10.3.0',
                   FileVersion='4.10.3.0',InformationalVersion='4.10.3+6c05fa33450ee3960f0763948e91327f049b302b',
                   IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',
                   EnableNETAnalyzers='false',NuGetAudit='false',SignAssembly='true',PublicSign='true',
                   AssemblyOriginatorKeyFile=relative(root/'Microsoft.public.snk')).items():ET.SubElement(props,k).text=v
    items=ET.SubElement(project,'ItemGroup')
    ET.SubElement(items,'Compile',Include=relative(root/'facades'/(assembly+'.cs')))
    reference=ET.SubElement(items,'Reference',Include='System.Private.ServiceModel')
    ET.SubElement(reference,'HintPath').text=relative(root/'System.Private.ServiceModel/bin/Release/net8.0/System.Private.ServiceModel.dll')
    ET.indent(project);ET.ElementTree(project).write(folder/'build.csproj',encoding='utf-8',xml_declaration=True)
