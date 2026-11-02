from pathlib import Path
import shutil,sys,xml.etree.ElementTree as E
source,prepared,inputs=(Path(p).resolve() for p in sys.argv[1:]);folder=prepared/'packages';folder.mkdir();payload=folder/'payload';payload.mkdir()
for name in ['DocumentationAnalyzers','DocumentationAnalyzers.CodeFixes']:
 shutil.copyfile(prepared/name/'bin/Release/net8.0'/(name+'.dll'),payload/(name+'.dll'))
shutil.copyfile(prepared/'DocumentationAnalyzers.CodeFixes/bin/Release/net8.0/CommonMark.dll',payload/'CommonMark.dll')
shutil.copyfile(inputs/'README.md',payload/'README.md')
for name in ['LICENSE','THIRD-PARTY-NOTICES.txt']:shutil.copyfile(source/name,payload/name)
for kind,id,version in [('implementation','DotNetAnalyzers.DocumentationAnalyzers.Unstable','1.0.0.59'),('meta','DotNetAnalyzers.DocumentationAnalyzers','1.0.0-beta.59')]:
 out=folder/kind;out.mkdir();package=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');metadata=E.SubElement(package,'metadata')
 for k,v in dict(id=id,version=version,authors='DocumentationAnalyzers contributors',description='Source-built .NET 8 DocumentationAnalyzers and code fixes.',developmentDependency='true',readme='README.md').items():E.SubElement(metadata,k).text=v
 E.SubElement(metadata,'license',type='expression').text='MIT'
 E.SubElement(metadata,'repository',type='git',url='https://github.com/DotNetAnalyzers/DocumentationAnalyzers',commit='489c06575beee224030ffdc9e91ce43569f32a79')
 if kind=='meta':E.SubElement(E.SubElement(metadata,'dependencies'),'dependency',id='DotNetAnalyzers.DocumentationAnalyzers.Unstable',version='[1.0.0.59]')
 files=E.SubElement(package,'files')
 for name in ['README.md','LICENSE','THIRD-PARTY-NOTICES.txt']:E.SubElement(files,'file',src='../payload/'+name,target=name)
 if kind=='implementation':
  for name in ['DocumentationAnalyzers.dll','DocumentationAnalyzers.CodeFixes.dll','CommonMark.dll']:E.SubElement(files,'file',src='../payload/'+name,target='analyzers/dotnet/cs/')
  for name in ['install.ps1','uninstall.ps1']:
   shutil.copyfile(source/'DocumentationAnalyzers/DocumentationAnalyzers.CodeFixes/tools'/name,payload/name);E.SubElement(files,'file',src='../payload/'+name,target='tools/')
  # Keep the source distribution alongside the analyzer assets, as upstream does.
  for name in ['DocumentationAnalyzers','DocumentationAnalyzers.CodeFixes']:
   target=payload/'src'/name;shutil.copytree(source/'DocumentationAnalyzers'/name,target,ignore=shutil.ignore_patterns('bin','obj'))
   for item in sorted(target.rglob('*.cs')):
    relative=item.relative_to(target).as_posix()
    E.SubElement(files,'file',src='../payload/src/'+name+'/'+relative,target='src/'+name+'/'+str(Path(relative).parent).replace('\\','/')+'/')
 E.indent(package);E.ElementTree(package).write(out/'Package.nuspec',encoding='utf-8',xml_declaration=True)
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',IncludeBuildOutput='false',EnableNETAnalyzers='false',NuGetAudit='false',NuspecFile='Package.nuspec',NuspecBasePath='$(MSBuildThisFileDirectory)',NoWarn='NU5128;NU5100').items():E.SubElement(props,k).text=v
 E.indent(project);E.ElementTree(project).write(out/'Package.csproj',encoding='utf-8',xml_declaration=True)
