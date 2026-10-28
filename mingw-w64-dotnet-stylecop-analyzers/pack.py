"""Stage both original package IDs, complete source-built assets and check data."""
from pathlib import Path
import json,shutil,sys,xml.etree.ElementTree as E

source,prepared,inputs=(Path(p).resolve() for p in sys.argv[1:])
packages=prepared/'packages';packages.mkdir();payload=packages/'payload';payload.mkdir()
data=prepared/'checkdata';data.mkdir()
for name in ['StyleCop.Analyzers','StyleCop.Analyzers.CodeFixes']:
 for item in sorted((prepared/name/'bin/Release/net8.0').rglob(name+'*.dll')):
  relative=item.relative_to(prepared/name/'bin/Release/net8.0')
  target=payload/'analyzers/dotnet/cs'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target)
for filename in ['localization.json','source-items.json','compatibility-wrappers.json']:
 shutil.copyfile(prepared/filename,data/filename)
shutil.copyfile(prepared/'fixtures.json',data/'fixtures.json')
for filename in ['ExpectedInventory.json','source-inputs.json','upstream-commit.txt','published-metadata-provenance.json']:
 shutil.copyfile(inputs/filename,data/filename)
relative=Path('StyleCop.Analyzers/StyleCop.Analyzers/Lightup/.generated/StyleCop.Analyzers.CodeGeneration')
for generator in ['OperationLightupGenerator','SyntaxLightupGenerator']:
 name='StyleCop.Analyzers.CodeGeneration.'+generator
 for kind,root,subpath in [('baseline',source,relative),('regenerated',prepared,Path('StyleCop.Analyzers/generated/StyleCop.Analyzers.CodeGeneration'))]:
  for item in sorted((root/subpath/name).glob('*.cs')):
   short='operation' if generator=='OperationLightupGenerator' else 'syntax'
   target=data/kind/short/item.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target)
manifest=json.loads((prepared/'source-items.json').read_text())
for name,entry in manifest.items():
 main=source/'StyleCop.Analyzers'/name
 for item in sorted(main.rglob('*.cs')):
  relative=item.relative_to(main)
  if any(p.startswith('.') for p in relative.parts):continue
  actual=item
  if item.relative_to(source).as_posix() in entry['overlays']:
   actual=prepared/name/item.name if name.endswith('CodeGeneration') else prepared/name/'overlays'/relative
  target=payload/'src'/name/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(actual,target)
 for item in sorted(main.rglob('*.resx')):
  target=payload/'src'/name/item.relative_to(main);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target)
for filename in ['OperationInterfaces.xml','Syntax.xml']:
 target=payload/'src/StyleCop.Analyzers/Lightup'/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/'StyleCop.Analyzers/StyleCop.Analyzers/Lightup'/filename,target)
for filename in ['LICENSE','THIRD-PARTY-NOTICES.txt']:shutil.copyfile(source/filename,payload/filename)
shutil.copyfile(inputs/'Apache-2.0.txt',payload/'Apache-2.0.txt')
shutil.copyfile(inputs/'README.md',payload/'README.md')
shutil.copytree(data,payload/'source-build/checkdata')
for kind,id,version in [('meta','StyleCop.Analyzers','1.2.0-beta.556'),('implementation','StyleCop.Analyzers.Unstable','1.2.0.556')]:
 folder=packages/kind;folder.mkdir();package=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');metadata=E.SubElement(package,'metadata')
 for k,v in dict(id=id,version=version,authors='StyleCop.Analyzers contributors',description='Source-built .NET 8 StyleCop analyzers and code fixes.',developmentDependency='true',readme='README.md').items():E.SubElement(metadata,k).text=v
 E.SubElement(metadata,'license',type='expression').text='MIT AND Apache-2.0'
 E.SubElement(metadata,'repository',type='git',url='https://github.com/DotNetAnalyzers/StyleCopAnalyzers',commit='73a46ae2e65e7870fefe35e2c4c12bb7152f4ec5')
 if kind=='meta':E.SubElement(E.SubElement(metadata,'dependencies'),'dependency',id='StyleCop.Analyzers.Unstable',version='[1.2.0.556]')
 files=E.SubElement(package,'files')
 for item in sorted(payload.rglob('*')):
  if not item.is_file():continue
  relative=item.relative_to(payload)
  if kind=='meta' and relative.as_posix() not in {'README.md','LICENSE','THIRD-PARTY-NOTICES.txt','Apache-2.0.txt'}:continue
  target=relative.name if relative.parent==Path('.') else relative.parent.as_posix()+'/'
  E.SubElement(files,'file',src='../payload/'+relative.as_posix(),target=target)
 E.indent(package);E.ElementTree(package).write(folder/'Package.nuspec',encoding='utf-8',xml_declaration=True)
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',IncludeBuildOutput='false',EnableNETAnalyzers='false',NuGetAudit='false',NuspecFile='Package.nuspec',NuspecBasePath='$(MSBuildThisFileDirectory)',NoWarn='NU5128;NU5100').items():E.SubElement(props,k).text=v
 E.indent(project);E.ElementTree(project).write(folder/'Package.csproj',encoding='utf-8',xml_declaration=True)
