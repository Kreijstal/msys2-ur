"""Preserve all eight original CodePages4.5.1 DLL paths and dependency groups."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();folder=root/'archive';folder.mkdir();(root/'feed').mkdir();provenance=json.loads((here/'inputs/published-provenance.json').read_text())
package=E.parse(here/'inputs/original.nuspec').getroot()
for node in package.iter():node.tag=node.tag.split('}')[-1]
md=package.find('metadata');assert md.findtext('id')=='System.Text.Encoding.CodePages' and md.findtext('version')=='4.5.1';md.find('authors').text+='; MSYS2 source bootstrap'
for name in ['licenseUrl','iconUrl','owners']:
 for node in md.findall(name):md.remove(node)
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='99ce22c306b07f99ddae60f443d23a983ae78f7b');md.find('description').text+='\nSource SDK8/Csc4.4 bootstrap, retaining harvested CoreFX4d1af962 and original CoreFX99ce22c3 source implementations.'
refs=E.SubElement(md,'references')
for tfm in ['MonoAndroid1.0','MonoTouch1.0','Xamarin.iOS1.0','Xamarin.Mac2.0','Xamarin.TVOS1.0','Xamarin.WatchOS1.0']:
 E.SubElement(E.SubElement(refs,'group',targetFramework=tfm),'reference',file='_._')
files=E.SubElement(package,'files')
for name in provenance['original_assets']:
 if name.endswith('.dll'):E.SubElement(files,'file',src=native(root/'assets'/name),target=name.rsplit('/',1)[0]+'/')
 else:
  assert name.endswith('/_._');E.SubElement(files,'file',src=native(root/'_._'),target=name.rsplit('/',1)[0]+'/')
for name,path in [('LICENSE.TXT',root/'sources/current/LICENSE.TXT'),('THIRD-PARTY-NOTICES.TXT',root/'sources/current/THIRD-PARTY-NOTICES.TXT'),('version.txt',root/'version.txt'),('useSharedDesignerContext.txt',root/'sources/current/pkg/useSharedDesignerContext.txt')]:E.SubElement(files,'file',src=native(path),target=name)
E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
assert E.parse(root/'sources/current/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NoWarn>NU5128</NoWarn><PackageId>System.Text.Encoding.CodePages</PackageId><Version>4.5.1</Version><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n');(folder/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(folder/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
