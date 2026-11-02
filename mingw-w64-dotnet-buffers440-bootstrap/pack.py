"""Package original runtime/reference assets, documentation and framework markers."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
folder=root/'archive';folder.mkdir();(root/'feed').mkdir()
package=E.Element('package');md=E.SubElement(package,'metadata')
for k,v in dict(id='System.Buffers',version='4.4.0',authors='Microsoft; MSYS2 source bootstrap',description='Original Buffers4.4 Standard1.1/2.0 implementation and reference profiles from CoreFX8321c729. Source SDK8/Csc4.4 bootstrap; original published XML documentation text retained as a disclosed data input.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='8321c729934c0f8be754953439b88e6e1c120c24')
deps=E.SubElement(md,'dependencies')
for tfm,items in json.loads((here/'inputs/published-provenance.json').read_text())['original_dependency_attributes'].items():
 group=E.SubElement(deps,'group',targetFramework=tfm)
 for item in items:E.SubElement(group,'dependency',**item)
references=E.SubElement(md,'references');E.SubElement(E.SubElement(references,'group',targetFramework='.NETCoreApp2.0'),'reference',file='_._')
for tfm in ['netstandard1.1','netstandard2.0']:
 group=E.SubElement(references,'group',targetFramework='.NETStandard'+tfm.removeprefix('netstandard'))
 for name in ['System.Buffers.dll','System.Buffers.xml']:E.SubElement(group,'reference',file=name)
files=E.SubElement(package,'files')
for kind in ['lib','ref']:
 E.SubElement(files,'file',src=native(root/'_._'),target=kind+'/netcoreapp2.0/')
 for tfm in ['netstandard1.1','netstandard2.0']:
  E.SubElement(files,'file',src=native(root/kind/tfm/'bin/Release/System.Buffers.dll'),target=kind+'/'+tfm+'/')
  E.SubElement(files,'file',src=native(here/'inputs/System.Buffers.xml'),target=kind+'/'+tfm+'/')
for name,path in [('LICENSE.TXT',root/'source/LICENSE.TXT'),('THIRD-PARTY-NOTICES.TXT',root/'source/THIRD-PARTY-NOTICES.TXT'),('version.txt',root/'version.txt'),('useSharedDesignerContext.txt',root/'source/pkg/useSharedDesignerContext.txt')]:E.SubElement(files,'file',src=native(path),target=name)
E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
# CoreFX Packaging.props explicitly skips this check for the original portable
# and Xamarin dependency groups, which intentionally have no matching assets.
# Translate that single upstream packaging policy; library compiler WAE stays on.
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NoWarn>NU5128</NoWarn><PackageId>System.Buffers</PackageId><Version>4.4.0</Version><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n');(folder/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(folder/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
