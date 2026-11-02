"""Evaluate all original dependency groups and pack with source NuGet.Packaging."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,xml.etree.ElementTree as E,zipfile

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);args=parser.parse_args()
root=args.root.resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(root/'cli-home'),NUGET_PACKAGES=native(root/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe';groups={}
for tfm in ['net6.0','net7.0','net8.0','netstandard2.0','netstandard2.1']:
 identifier='.NETStandard' if tfm.startswith('netstandard') else '.NETCoreApp'
 command=[dotnet,'msbuild',native(root/'Evaluate.proj'),'-nologo','-v:q','-getItem:PackageReference','-p:TargetFramework='+tfm,'-p:TargetFrameworkIdentifier='+identifier]
 result=subprocess.run(command,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (root/(tfm+'-evaluation.json')).write_text(result.stdout);assert result.returncode==0,result.stdout
 data=json.loads(result.stdout);items=data['Items']['PackageReference'];groups[tfm]={item['Identity']:item['Version'] for item in items};assert len(groups[tfm])==len(items)
assert {t:len(v) for t,v in groups.items()}=={'net6.0':35,'net7.0':35,'net8.0':35,'netstandard2.0':44,'netstandard2.1':42}
versions=E.parse(root/'source/eng/Versions.props');version='.'.join(versions.findtext('.//'+name) for name in ['MajorVersion','MinorVersion','PatchVersion']);assert version=='8.0.31'
project=E.parse(root/'upstream.proj');package=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');metadata=E.SubElement(package,'metadata')
for name,value in dict(id='Microsoft.Windows.Compatibility',version=version,authors='Microsoft',description=project.findtext('.//PackageDescription'),readme='PACKAGE.md',icon='Icon.png',projectUrl='https://dot.net/',serviceable='true').items():E.SubElement(metadata,name).text=value
E.SubElement(metadata,'license',type='expression').text='MIT';E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/windowsdesktop',commit='337963009d48a3016b50172b451b4e80f78791a7')
deps=E.SubElement(metadata,'dependencies')
for tfm,items in groups.items():
 group=E.SubElement(deps,'group',targetFramework=tfm)
 for name,minimum in sorted(items.items()):E.SubElement(group,'dependency',id=name,version=minimum,exclude='Build,Analyzers')
shutil.copy2(root/'source/src/Microsoft.Windows.Compatibility/src/PACKAGE.md',root/'PACKAGE.md')
shutil.copy2(root/'source/LICENSE',root/'LICENSE')
files=E.SubElement(package,'files')
for name in ['PACKAGE.md','Icon.png','LICENSE','Arcade-LICENSE.TXT']:E.SubElement(files,'file',src=name,target=name)
E.ElementTree(package).write(root/'Microsoft.Windows.Compatibility.nuspec',encoding='utf-8',xml_declaration=True)
tool=root/'pack-tool';tool.mkdir(exist_ok=True);shutil.copy2(here/'Pack.cs',tool/'Program.cs')
(tool/'Pack.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><Compile Include="Program.cs"/><PackageReference Include="NuGet.Packaging" Version="[6.9.1]"/></ItemGroup></Project>\n')
(root/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
with (root/'pack-tool-build.log').open('w') as log:subprocess.run([dotnet,'build',native(tool/'Pack.csproj'),'-c','Release','--configfile',native(root/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,check=True,stdout=log,stderr=subprocess.STDOUT)
feed=root/'feed';feed.mkdir(exist_ok=True);output=feed/('microsoft.windows.compatibility.'+version+'.nupkg')
subprocess.run([dotnet,native(tool/'bin/Release/net8.0/Pack.dll'),native(root/'Microsoft.Windows.Compatibility.nuspec'),native(output)],env=env,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Packaging tools are restored from the installed source feed too.
owners={}
for cache in (root/'cache').rglob('*.nupkg'):
 installed=Path('/clang64/lib/dotnet/library-packs')/cache.name;assert installed.is_file() and sha(installed)==sha(cache),cache
 owners[cache.name]=dict(source_archive_sha256=sha(cache),native_owner=subprocess.check_output(['pacman','-Qqo',str(installed)],text=True).strip())
(root/'dependency-groups.json').write_text(json.dumps(groups,indent=2)+'\n')
(root/'build-audit.json').write_text(json.dumps(dict(original_dependency_groups=groups,all_five_framework_groups_preserved=True,total_dependency_entries=sum(map(len,groups.values())),package_sha256=sha(output),source_pack_tool_dependency_owners=owners,production_library_payloads=0),indent=2)+'\n')
print('PASS source NuGet.Packaging produced complete five-framework metapackage:',sum(map(len,groups.values())),'dependency entries; source dependency closure/consumer checks remain required')
