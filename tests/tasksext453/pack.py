"""Package the original two implementation profiles and dependency groups."""
from pathlib import Path
import os,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();here=Path(__file__).parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
folder=root/'archive';folder.mkdir();(root/'feed').mkdir()
package=E.parse(here/'inputs/original.nuspec').getroot()
for node in package.iter():node.tag=node.tag.split('}')[-1]
md=package.find('metadata');assert md.findtext('id')=='System.Threading.Tasks.Extensions' and md.findtext('version')=='4.5.3'
md.find('authors').text+='; MSYS2 source bootstrap'
for name in ['licenseUrl','iconUrl','owners']:
 for node in md.findall(name):md.remove(node)
E.SubElement(md,'license',type='expression').text='MIT'
E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='637a8d58f72f2b0f1a71187530c3cf433e95a75a')
md.find('description').text+='\nSource SDK8/Csc4.4 bootstrap. Original published XML documentation is retained as a disclosed nonexecutable text input.'
references=E.SubElement(md,'references')
for tfm in ['MonoAndroid1.0','MonoTouch1.0','.NETCoreApp2.1','Xamarin.iOS1.0','Xamarin.Mac2.0','Xamarin.TVOS1.0','Xamarin.WatchOS1.0']:E.SubElement(E.SubElement(references,'group',targetFramework=tfm),'reference',file='_._')
files=E.SubElement(package,'files')
for tfm in ['netstandard1.0','netstandard2.0','portable-net45+win8+wp8+wpa81']:
 E.SubElement(files,'file',src=native(root/'lib'/tfm/'bin/Release/System.Threading.Tasks.Extensions.dll'),target='lib/'+tfm+'/')
 E.SubElement(files,'file',src=native(here/'inputs'/('documentation-'+tfm+'.xml')),target='lib/'+tfm+'/System.Threading.Tasks.Extensions.xml')
for kind in ['lib','ref']:
 for tfm in ['MonoAndroid10','MonoTouch10','netcoreapp2.1','xamarinios10','xamarinmac20','xamarintvos10','xamarinwatchos10']:E.SubElement(files,'file',src=native(root/'_._'),target=kind+'/'+tfm+'/')
for name,path in [('LICENSE.TXT',root/'source/LICENSE.TXT'),('THIRD-PARTY-NOTICES.TXT',root/'source/THIRD-PARTY-NOTICES.TXT'),('version.txt',root/'version.txt'),('useSharedDesignerContext.txt',root/'source/pkg/useSharedDesignerContext.txt')]:E.SubElement(files,'file',src=native(path),target=name)
E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NoWarn>NU5128;NU5130</NoWarn><PackageId>System.Threading.Tasks.Extensions</PackageId><Version>4.5.3</Version><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n')
(folder/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(folder/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
