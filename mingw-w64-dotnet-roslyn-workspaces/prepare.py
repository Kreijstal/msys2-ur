"""Build complete .NET 8 workspace assemblies from the pinned Roslyn source tree."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
inputs=Path(__file__).parent
shutil.copyfile(inputs/'README.md',out/'README.md')
common=Path(os.path.commonpath([source,out]))
base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
def tag(e):return e.tag.rsplit('}',1)[-1]
settings=E.parse(source/'eng/targets/Settings.props')
def key_value(name):
 value=next(e.text for e in settings.iter(name));seen={name}
 while re.fullmatch(r'\$\((\w+)\)',value):
  name=value[2:-1];assert name not in seen,seen;seen.add(name)
  value=next(e.text for e in settings.iter(name))
 assert re.fullmatch('[0-9a-fA-F]+',value),value
 return value
key=key_value('MicrosoftSharedPublicKey');assert hashlib.sha1(bytes.fromhex(key)).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Roslyn.public.snk').write_bytes(bytes.fromhex(key))
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib'}:
  removed.append({'path':f.relative_to(source).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()});f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
localizations=[];source_items={}
def resource(items,folder,path,classname,logical=None):
 logical=logical or classname
 namespace,_,leaf=classname.rpartition('.')
 code=['#nullable enable',f'namespace {namespace} {{ internal static class {leaf} {{',f'internal static System.Resources.ResourceManager ResourceManager {{get;}} = new System.Resources.ResourceManager({json.dumps(logical)},typeof({leaf}).Assembly);','internal static System.Globalization.CultureInfo? Culture {get;set;}']
 strings={}
 for data in E.parse(path).iter('data'):
  assert not data.get('type') and not data.get('mimetype'),path
  name=data.get('name');identifier=re.sub(r'[^A-Za-z0-9_]','_',name);assert identifier.isidentifier(),name
  strings[name]=data.findtext('value') or ''
  code.append(f'internal static string {identifier} => ResourceManager.GetString({json.dumps(name)},Culture)!;')
 code.append('}}');generated=folder/(classname+'.g.cs');generated.write_text('\n'.join(code)+'\n')
 E.SubElement(items,'Compile',Include=native(generated))
 E.SubElement(items,'EmbeddedResource',Include=native(path),LogicalName=logical+'.resources')
 localizations.append(dict(assembly=folder.name,resource=logical,culture='',strings=strings))
 ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
 for translation in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
  xlf=E.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
  values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
  localized=E.parse(path)
  for data in localized.iter('data'):
   if data.get('name') in values:data.find('value').text=values[data.get('name')]
  target=folder/(logical+'.'+culture+'.resx');localized.write(target,encoding='utf-8',xml_declaration=True)
  E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
  localizations.append(dict(assembly=folder.name,resource=logical,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))

for language,name,pkgid,deps in [
 ('Core','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.Workspaces.Common',{'Microsoft.CodeAnalysis.Common':'4.9.2','Humanizer.Core':'2.14.1','System.Composition':'8.0.0','System.IO.Pipelines':'8.0.0'}),
 ('CSharp','Microsoft.CodeAnalysis.CSharp.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces',{'Microsoft.CodeAnalysis.Common':'4.9.2','Microsoft.CodeAnalysis.CSharp':'4.9.2','Microsoft.CodeAnalysis.Workspaces.Common':'4.9.2','Humanizer.Core':'2.14.1'})]:
 folder=out/name;folder.mkdir();main=source/'src/Workspaces'/language/'Portable';original=E.parse(main/(name+'.csproj')).getroot()
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace='Microsoft.CodeAnalysis'+('.CSharp' if language=='CSharp' else ''),PackageId=pkgid,Version='4.9.2',AssemblyVersion='4.9.0.0',FileVersion='4.9.2.0',InformationalVersion='4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',AllowUnsafeBlocks='true',Nullable='enable',LangVersion='12.0',DefineConstants='$(DefineConstants);WORKSPACE;DOTNET_BUILD_FROM_SOURCE',DotNetBuildFromSource='true',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Roslyn.public.snk'),PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/roslyn',RepositoryCommit='9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',NoWarn='CS0436;CS0618;SYSLIB0051;SYSLIB0050',PackageReadmeFile='README.md')
 for k,v in values.items():E.SubElement(props,k).text=v
 items=E.SubElement(p,'ItemGroup')
 E.SubElement(items,'None',Include=native(out/'README.md'),Pack='true',PackagePath='/')
 for dep,version in deps.items():E.SubElement(items,'PackageReference',Include=dep,Version='['+version+']')
 files=set();resources={};visited=set()
 for f in main.rglob('*.cs'):
  if language=='Core' and 'Storage/SQLite/' in f.relative_to(main).as_posix():continue
  files.add(f.resolve())
 def collect(project,namespace):
  if project in visited:return
  visited.add(project);tree=E.parse(project).getroot()
  for group in tree:
   if tag(group)=='PropertyGroup':
    for e in group:
     if tag(e)=='Import_RootNamespace':namespace=e.text
  for group in tree:
   if tag(group)=='Import':
    relative=group.get('Project');assert '$(' not in relative,(project,relative)
    imported=(project.parent/relative.replace('\\','/')).resolve();assert imported.suffix=='.projitems',imported
    collect(imported,namespace)
   elif tag(group)=='ItemGroup':
    for e in group:
     kind=tag(e)
     if kind=='Compile' and e.get('Include'):
      assert not group.get('Condition') and e.get('Condition') in {None,"'$(DotNetBuildFromSource)' == 'true'"},(project,E.tostring(e))
      relative=e.get('Include').replace('$(MSBuildThisFileDirectory)',str(project.parent)+'/').replace('\\','/')
      assert '$(' not in relative and '*' not in relative,(project,relative)
      files.add((project.parent/relative).resolve())
     elif kind=='EmbeddedResource' and (e.get('Include') or e.get('Update')):
      relative=(e.get('Include') or e.get('Update')).replace('$(MSBuildThisFileDirectory)',str(project.parent)+'/').replace('\\','/')
      path=(project.parent/relative).resolve();assert path.suffix=='.resx',path
      cls=e.get('ClassName') or values['RootNamespace']+'.'+path.stem
      logical=cls if not cls.endswith('.SR') else cls.rsplit('.',1)[0]+'.'+path.stem
      resources[path]=(cls,logical)
 collect(main/(name+'.csproj'),values['RootNamespace'])
 if language=='Core':files.add(source/'src/Compilers/Core/Portable/InternalUtilities/PerformanceSensitiveAttribute.cs')
 for f in sorted(files):assert f.is_file(),f;E.SubElement(items,'Compile',Include=native(f))
 for path,(cls,logical) in sorted(resources.items()):resource(items,folder,path,cls,logical)
 declarations=[]
 for friend in original.iter():
  if tag(friend) not in {'InternalsVisibleTo','RestrictedInternalsVisibleTo'}:continue
  public=friend.get('Key');public=key_value(public[2:-1]) if public else key
  declarations.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(friend.get('Include')+', PublicKey='+public)+')]')
  if tag(friend)=='RestrictedInternalsVisibleTo':
   ns=friend.get('Namespace') or 'Microsoft.CodeAnalysis.ExternalAccess.'+friend.get('Partner')+'.Api'
   declarations.append('[assembly: System.Runtime.CompilerServices.RestrictedInternalsVisibleTo('+json.dumps(friend.get('Include'))+','+json.dumps(ns)+')]')
 attrs=folder/'Friends.g.cs';attrs.write_text('\n'.join(declarations)+'\n');E.SubElement(items,'Compile',Include=native(attrs))
 E.indent(p);E.ElementTree(p).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
 source_items[name]=dict(source_files=len(files),imports=[str(f.relative_to(source)) for f in sorted(visited)],resources=[str(r.relative_to(source)) for r in sorted(resources)],friend_declarations=len(declarations),friend_attributes=declarations,dependencies=deps)
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
(out/'source-items.json').write_text(json.dumps(source_items,indent=2)+'\n')
installed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for label,path in [('private',out.parent/'feed'),('installed',installed)]:
 value=subprocess.check_output(['cygpath','-am',str(path)],text=True).strip() if shutil.which('cygpath') else str(path)
 E.SubElement(sources,'add',key=label,value=value)
E.indent(config);E.ElementTree(config).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
