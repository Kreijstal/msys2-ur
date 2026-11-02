"""Stage the full source-built analyzer package, original generated assets and sources."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E
source,prepared,inputs=(Path(p).resolve() for p in sys.argv[1:]);package=prepared/'package';package.mkdir();payload=package/'payload';payload.mkdir()
def copy(src,relative):
 target=payload/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
core='Microsoft.CodeAnalysis.NetAnalyzers'
for language,name in [('cs','Microsoft.CodeAnalysis.CSharp.NetAnalyzers'),('vb','Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers')]:
 for assembly in [core,name]:
  root=prepared/assembly/'bin/Release/net8.0'
  for path in sorted(root.rglob(assembly+'*.dll')):copy(path,Path('analyzers/dotnet')/language/path.relative_to(root))
for path in sorted((prepared/'generated').rglob('*')):
 if not path.is_file():continue
 relative=path.relative_to(prepared/'generated');kind=relative.parts[0]
 if kind=='inputs':continue
 relative=Path(relative.as_posix().replace('globalconfig/','buildTransitive/config/').replace('docs/','documentation/'))
 copy(path,relative)
for src,target in [('assets/install.ps1','tools/install.ps1'),('assets/uninstall.ps1','tools/uninstall.ps1'),('assets/ThirdPartyNotices.txt','ThirdPartyNotices.txt'),('License.txt','License.txt'),('docs/Analyzer Configuration.md','documentation/Analyzer Configuration.md'),('src/NetAnalyzers/readme.md','documentation/readme.md')]:copy(source/src,target)
copy(inputs/'README.md','README.md')
for filename in ['ExpectedAssemblies.json','ExpectedLegacyEmpty.json','ExpectedGeneratedAssets.json','UpstreamFixtures.json','published-metadata-provenance.json']:
 copy(inputs/filename,Path('source-build')/filename)
for filename in ['fixtures.json','localization.json','source-items.json','removed-binaries.json']:copy(prepared/filename,Path('source-build')/filename)
manifest=json.loads((prepared/'source-items.json').read_text());source_paths=set();resource_paths=set()
for entry in manifest.values():
 source_paths.update(entry['source_paths']);resource_paths.update(entry.get('embedded',[]))
source_paths.update(path for item in manifest.values() for path in item.get('imports',[]))
for relative in list(resource_paths):
 original=source/relative
 if original.suffix=='.resx':resource_paths.update(x.relative_to(source).as_posix() for x in (original.parent/'xlf').glob(original.stem+'.*.xlf'))
source_map={relative:'s/'+hashlib.sha256(relative.encode()).hexdigest()[:20]+Path(relative).suffix for relative in sorted(source_paths|resource_paths)}
assert len(set(source_map.values()))==len(source_map)
for relative,target in source_map.items():copy(source/relative,target)
for name,entry in manifest.items():
 for original,port in entry.get('source_substitutions',{}).items():copy(prepared/name/(Path(original).stem+'.port'+Path(original).suffix),'s/ported/'+Path(original).name)
for language in ['Core','CSharp','VisualBasic']:
 for filename in ['AnalyzerReleases.Shipped.md','AnalyzerReleases.Unshipped.md']:
  copy(source/'src/NetAnalyzers'/language/filename,'source-build/releases/'+language+'/'+filename)
(payload/'source-build/source-map.json').write_text(json.dumps(source_map,indent=2)+'\n')
for filename in ['prepare.py','build-libraries.sh','generate-config.sh','ExtractFixtures.cs','pack.py','verify-generated.py']:copy(inputs/filename,'source-build/recipe/'+filename)
nuspec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');metadata=E.SubElement(nuspec,'metadata')
for k,v in dict(id='Microsoft.CodeAnalysis.NetAnalyzers',version='8.0.0-preview.26274.2',authors='Roslyn Analyzers contributors',description='Full SDK-selected source-built .NET analyzers and CSharp/VisualBasic code fixes for .NET8/Roslyn4.9.2.',developmentDependency='true',readme='README.md').items():E.SubElement(metadata,k).text=v
E.SubElement(metadata,'license',type='expression').text='MIT'
E.SubElement(metadata,'repository',type='git',url='https://github.com/dotnet/roslyn-analyzers',commit='0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4')
files=E.SubElement(nuspec,'files')
for path in sorted(payload.rglob('*')):
 if not path.is_file():continue
 relative=path.relative_to(payload);target=relative.name if relative.parent==Path('.') else relative.parent.as_posix()+'/'
 assert path.suffix.lower() not in {'.snk','.pdb','.p7s','.nupkg'},relative
 E.SubElement(files,'file',src='payload/'+relative.as_posix(),target=target)
E.indent(nuspec);E.ElementTree(nuspec).write(package/'Package.nuspec',encoding='utf-8',xml_declaration=True)
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',IncludeBuildOutput='false',EnableNETAnalyzers='false',NuGetAudit='false',NuspecFile='Package.nuspec',NuspecBasePath='$(MSBuildThisFileDirectory)',NoDefaultExcludes='true',NoWarn='NU5128;NU5100').items():E.SubElement(props,k).text=v
E.indent(project);E.ElementTree(project).write(package/'Package.csproj',encoding='utf-8',xml_declaration=True)
__import__('subprocess').run([sys.executable,str(inputs/'verify-generated.py'),str(payload),str(inputs/'ExpectedGeneratedAssets.json')],check=True)
print('Staged full source NetAnalyzers package, original generated text and complete build/source provenance')
