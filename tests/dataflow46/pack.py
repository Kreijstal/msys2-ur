"""Package both original profiles and a disclosed byte-identical NS2 compatibility asset."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
provenance=json.loads((here/'inputs/published-provenance.json').read_text())
folder=root/(sys.argv[2] if len(sys.argv)==3 else 'archive');folder.mkdir();(root/'feed').mkdir(exist_ok=True)
assert not list((root/'feed').glob('*.nupkg'))
package=E.Element('package');md=E.SubElement(package,'metadata')
for k,v in dict(id='System.Threading.Tasks.Dataflow',version='4.6.0',authors='Microsoft; MSYS2 source bootstrap',description='Original Dataflow4.6 Standard1.0/1.1 source builds; source SDK8/Csc4.4 bootstrap. The Standard2 compatibility asset is byte-identical to the original-profile Standard1.1 implementation. Historical runtime closure remains separate work.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT'
E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='9688ddbb62c04189cac4c4a06e31e93377dccd41')
groups=dict(provenance['original_dependency_groups']);groups['.NETStandard2.0']={'NETStandard.Library':'[2.0.3]'}
deps=E.SubElement(md,'dependencies')
for tfm,items in groups.items():
    group=E.SubElement(deps,'group',targetFramework=tfm)
    for name,version in items.items():E.SubElement(group,'dependency',id=name,version=version)
files=E.SubElement(package,'files')
for target,source in [('netstandard1.0','netstandard1.0'),('netstandard1.1','netstandard1.1'),('netstandard2.0','netstandard1.1')]:
    binary=root/source/'bin/Release'/source
    E.SubElement(files,'file',src=native(binary/'System.Threading.Tasks.Dataflow.dll'),target='lib/'+target+'/')
    E.SubElement(files,'file',src=native(binary/'System.Threading.Tasks.Dataflow.XML'),target='lib/'+target+'/System.Threading.Tasks.Dataflow.xml')
for lic in ['LICENSE','THIRD-PARTY-NOTICES']:E.SubElement(files,'file',src=native(root/'source'/lic),target=lic)
E.indent(package);E.ElementTree(package).write(folder/'System.Threading.Tasks.Dataflow.nuspec',encoding='utf-8',xml_declaration=True)
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><PackageId>System.Threading.Tasks.Dataflow</PackageId><Version>4.6.0</Version><NuspecFile>'+native(folder/'System.Threading.Tasks.Dataflow.nuspec')+'</NuspecFile></PropertyGroup></Project>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(root/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
