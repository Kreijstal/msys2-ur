"""Package all original Unsafe4.5.2 runtime and compiler reference profiles."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
folder=root/'archive';folder.mkdir();(root/'feed').mkdir()
package=E.Element('package');md=E.SubElement(package,'metadata')
for k,v in dict(id='System.Runtime.CompilerServices.Unsafe',version='4.5.2',authors='Microsoft; MSYS2 source bootstrap',description='Original Unsafe4.5.2 IL and compiler references from CoreFX02b11eee, all shipped profiles. Source ILAsm10/SDK8/Csc4.4 bootstrap. Original publisher version strings retained; actual source provenance is in the package documentation.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='02b11eeee1fbc5f3ef43a1452fe07efd25fa1715')
deps=E.SubElement(md,'dependencies')
for tfm,dependencies in json.loads((here/'inputs/published-provenance.json').read_text())['original_dependency_groups'].items():
 group=E.SubElement(deps,'group',targetFramework=tfm)
 for ident,version in dependencies.items():E.SubElement(group,'dependency',id=ident,version=version)
files=E.SubElement(package,'files');source=root/'source/src/System.Runtime.CompilerServices.Unsafe/src/System.Runtime.CompilerServices.Unsafe.xml'
for tfm in ['netstandard1.0','netstandard2.0','netcoreapp2.0']:
 E.SubElement(files,'file',src=native(root/tfm/'System.Runtime.CompilerServices.Unsafe.dll'),target='lib/'+tfm+'/')
 E.SubElement(files,'file',src=native(source),target='lib/'+tfm+'/')
references=E.SubElement(md,'references')
for tfm in ['netstandard1.0','netstandard2.0']:
 E.SubElement(files,'file',src=native(root/'ref'/tfm/'System.Runtime.CompilerServices.Unsafe.dll'),target='ref/'+tfm+'/')
 group=E.SubElement(references,'group',targetFramework='.NETStandard'+tfm.removeprefix('netstandard'))
 E.SubElement(group,'reference',file='System.Runtime.CompilerServices.Unsafe.dll')
for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:E.SubElement(files,'file',src=native(root/'source'/lic),target=lic)
E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><PackageId>System.Runtime.CompilerServices.Unsafe</PackageId><Version>4.5.2</Version><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n')
(folder/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(folder/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
