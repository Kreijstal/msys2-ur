"""Package every original Vectors4.4 DLL/XML profile and framework marker."""
from pathlib import Path
import json,os,subprocess,sys,urllib.parse,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).parent;native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();provenance=json.loads((here/'inputs/published-provenance.json').read_text())
folder=root/'archive';folder.mkdir();(root/'feed').mkdir();package=E.Element('package');md=E.SubElement(package,'metadata')
for k,v in dict(id='System.Numerics.Vectors',version='4.4.0',authors='Microsoft; MSYS2 source bootstrap',description='Original Vectors4.4 Standard1.0/2.0, NET46 partial-facade and portable profiles from CoreFX8321c729. Source SDK8/Csc4.4 bootstrap; original published XML documentation retained as nonexecutable text input.').items():E.SubElement(md,k).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/corefx',commit='8321c729934c0f8be754953439b88e6e1c120c24')
deps=E.SubElement(md,'dependencies')
for tfm,items in provenance['original_dependency_attributes'].items():
 group=E.SubElement(deps,'group',targetFramework=tfm)
 for item in items:E.SubElement(group,'dependency',**item)
references=E.SubElement(md,'references')
for tfm in ['.NETFramework4.6','.NETStandard1.0','.NETStandard2.0']:
 group=E.SubElement(references,'group',targetFramework=tfm)
 for name in ['System.Numerics.Vectors.dll','System.Numerics.Vectors.xml']:E.SubElement(group,'reference',file=name)
marker_frameworks={'MonoAndroid10':'MonoAndroid1.0','MonoTouch10':'MonoTouch1.0','netcoreapp2.0':'.NETCoreApp2.0','xamarinios10':'Xamarin.iOS1.0','xamarinmac20':'Xamarin.Mac2.0','xamarintvos10':'Xamarin.TVOS1.0','xamarinwatchos10':'Xamarin.WatchOS1.0'}
for tfm in marker_frameworks.values():E.SubElement(E.SubElement(references,'group',targetFramework=tfm),'reference',file='_._')
files=E.SubElement(package,'files')
for name in provenance['DLL_asset_sha256']:
 decoded=urllib.parse.unquote(name);kind,tfm,file=decoded.split('/');E.SubElement(files,'file',src=native(root/kind/tfm/'bin/Release'/file),target=kind+'/'+tfm+'/')
for name,file in provenance['XML_input_file'].items():E.SubElement(files,'file',src=native(here/'inputs'/file),target=urllib.parse.unquote(name))
for name in provenance['empty_markers']:E.SubElement(files,'file',src=native(root/'_._'),target=name.rsplit('/',1)[0]+'/')
for name,path in [('LICENSE.TXT',root/'source/LICENSE.TXT'),('THIRD-PARTY-NOTICES.TXT',root/'source/THIRD-PARTY-NOTICES.TXT'),('version.txt',root/'version.txt'),('useSharedDesignerContext.txt',root/'source/pkg/useSharedDesignerContext.txt')]:E.SubElement(files,'file',src=native(path),target=name)
E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
# The original SkipValidatePackageTargetFramework covers both absent and
# compatible-but-not-identical groups, including the historical portable alias.
assert E.parse(root/'source/Packaging.props').findtext('.//{*}SkipValidatePackageTargetFramework')=='true'
(folder/'Archive.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><IncludeBuildOutput>false</IncludeBuildOutput><EnableDefaultItems>false</EnableDefaultItems><NuGetAudit>false</NuGetAudit><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NoWarn>NU5128;NU5130</NoWarn><PackageId>System.Numerics.Vectors</PackageId><Version>4.4.0</Version><NuspecFile>Package.nuspec</NuspecFile></PropertyGroup></Project>\n');(folder/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','pack',native(folder/'Archive.csproj'),'-c','Release','--configfile',native(folder/'NuGet.config'),'-p:UseSharedCompilation=false','-o',native(root/'feed'),'-v:minimal'],env=env,check=True)
