"""Retarget the original Pager project; retain both original C# sources unchanged."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as E

source,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
shutil.copytree(source/'src',output/'src')
project=output/'src/Microsoft.PowerShell.Pager.csproj'
tree=E.parse(project)
props=tree.getroot().find('PropertyGroup')
framework=props.find('TargetFrameworks');framework.tag='TargetFramework';framework.text='net8.0'
for name,value in dict(Version='1.0.0',AssemblyVersion='1.0.0.0',FileVersion='1.0.0.0',
    InformationalVersion='1.0.0',IncludeSourceRevisionInInformationalVersion='false',
    EnableNETAnalyzers='false',NuGetAudit='false',PackageId='Microsoft.PowerShell.Pager',
    Authors='Microsoft Corporation',Description='Complete source PowerShell Pager for.NET8',
    PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/PowerShell/Pager',
    RepositoryCommit='965675f549dfa074eb02a47ca6d6e07d0ee7771f',PackageReadmeFile='README.md').items():E.SubElement(props,name).text=value
items=E.SubElement(tree.getroot(),'ItemGroup')
for path,target in [('../README.md',''),('../LICENSE',''),('../source-inventory.json','source-build/')]:
    E.SubElement(items,'None',Include=path,Pack='true',PackagePath=target)
E.indent(tree);tree.write(project,encoding='utf-8',xml_declaration=True)
inventory={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source/'src').glob('*.cs'))}
assert len(inventory)==2
(output/'source-inventory.json').write_text(json.dumps(dict(source_commit='965675f549dfa074eb02a47ca6d6e07d0ee7771f',original_cs_sources=inventory,production_csharp_changes=0,target_framework='net8.0'),indent=2)+'\n')
shutil.copyfile(source/'LICENSE',output/'LICENSE')
shutil.copyfile(Path(__file__).resolve().with_name('README.md'),output/'README.md')
