"""Build all original Visual Basic Workspaces inputs against source .NET 8."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
common=Path(os.path.commonpath([source,out]))
base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
def tag(e):return e.tag.rsplit('}',1)[-1]
settings=E.parse(source/'eng/targets/Settings.props')
def key_value(name):
 value=next(e.text for e in settings.iter(name));seen={name}
 while re.fullmatch(r'\$\((\w+)\)',value):
  name=value[2:-1];assert name not in seen;seen.add(name);value=next(e.text for e in settings.iter(name))
 assert re.fullmatch('[0-9a-fA-F]+',value);return value
key=bytes.fromhex(key_value('MicrosoftSharedPublicKey'))
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Roslyn.public.snk').write_bytes(key)
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib'}:
  removed.append(dict(path=f.relative_to(source).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()));f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
name='Microsoft.CodeAnalysis.VisualBasic.Workspaces';folder=out/name;folder.mkdir()
main=source/'src/Workspaces/VisualBasic/Portable';original=E.parse(main/(name+'.vbproj')).getroot()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace='',PackageId=name,Version='4.9.2',AssemblyVersion='4.9.0.0',FileVersion='4.9.2.0',InformationalVersion='4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',VBRuntime='Embed',MyType='Empty',OptionExplicit='On',OptionInfer='On',OptionCompare='Binary',LangVersion='latest',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Roslyn.public.snk'),PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/roslyn',RepositoryCommit='9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',PackageReadmeFile='README.md',NoWarn='40057',DefineConstants='$(DefineConstants),WORKSPACE=True')
for k,v in values.items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
E.SubElement(items,'None',Include=native(Path(__file__).with_name('README.md')),Pack='true',PackagePath='/')
deps={n:'4.9.2' for n in ['Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.VisualBasic','Microsoft.CodeAnalysis.Workspaces.Common']}
for dep,version in deps.items():E.SubElement(items,'PackageReference',Include=dep,Version='['+version+']')
# Original Settings.props imports plus every Import from the original project/shared items.
imports={'Microsoft.VisualBasic','System','System.Collections','System.Collections.Generic','System.Diagnostics','System.Linq'}
files={f.resolve() for f in main.rglob('*.vb') if f.relative_to(main).parts[0]!='My Project'}
resources={};visited=set()
def collect(project,namespace=''):
 if project in visited:return
 visited.add(project);tree=E.parse(project).getroot()
 for group in tree:
  if tag(group)=='PropertyGroup':
   for e in group:
    if tag(e)=='Import_RootNamespace':namespace=e.text
 for group in tree:
  if tag(group)=='Import':
   relative=group.get('Project');assert '$(' not in relative,(project,relative)
   target=(project.parent/relative.replace('\\','/')).resolve();assert target.suffix=='.projitems';collect(target,namespace)
  elif tag(group)=='ItemGroup':
   for e in group:
    kind=tag(e)
    if kind=='Import':imports.add(e.get('Include'))
    elif kind=='Compile' and e.get('Include'):
     assert not e.get('Condition') and not group.get('Condition'),(project,E.tostring(e))
     relative=e.get('Include').replace('$(MSBuildThisFileDirectory)',str(project.parent)+'/').replace('\\','/')
     assert '$(' not in relative and '*' not in relative;files.add((project.parent/relative).resolve())
    elif kind=='EmbeddedResource' and (e.get('Include') or e.get('Update')):
     relative=(e.get('Include') or e.get('Update')).replace('$(MSBuildThisFileDirectory)',str(project.parent)+'/').replace('\\','/')
     path=(project.parent/relative).resolve();assert path.suffix=='.resx'
     cls=e.get('ClassName') or ((e.get('Namespace') or e.get('NAmespace') or values['RootNamespace'])+'.'+path.stem).lstrip('.')
     resources[path]=cls
collect(main/(name+'.vbproj'))
for ns in sorted(imports):E.SubElement(items,'Import',Include=ns)
for f in sorted(files):assert f.is_file(),f;E.SubElement(items,'Compile',Include=native(f))
friends=[]
for f in original.iter('InternalsVisibleTo'):
 public=f.get('Key');public=key_value(public[2:-1]) if public else key.hex()
 friends.append(f.get('Include')+', PublicKey='+public)
attrs=folder/'Friends.g.vb';attrs.write_text('\n'.join('<Assembly: Global.System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(f)+')>' for f in friends)+'\n');E.SubElement(items,'Compile',Include=native(attrs))
# Original Imports.targets WorkAroundDotnetSdk10591 for VBRuntime=Embed.
target=E.SubElement(p,'Target',Name='RemoveEmbeddedVbRuntimeReferences',AfterTargets='ResolveTargetingPackAssets')
E.SubElement(E.SubElement(target,'ItemGroup'),'Reference',Remove='@(Reference)',Condition="'%(FileName)' == 'Microsoft.VisualBasic' or '%(FileName)' == 'Microsoft.VisualBasic.Core'")
localizations=[]
def write_resx(tree,path):
 for data in tree.iter('data'):
  v=data.find('value')
  if v is not None:v.text=(v.text or '').replace('\r\n','\n').replace('\n','\r\n')
 path.write_bytes(E.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True).replace(b'\r',b'&#13;'))
for path,cls in sorted(resources.items()):
 namespace,_,leaf=cls.rpartition('.')
 code=(['Namespace '+namespace] if namespace else [])+['Friend NotInheritable Class '+leaf,'Private Sub New()','End Sub','Private Shared ReadOnly Manager As New Global.System.Resources.ResourceManager("'+cls+'",GetType('+leaf+').Assembly)','Friend Shared ReadOnly Property ResourceManager As Global.System.Resources.ResourceManager','Get','Return Manager','End Get','End Property','Friend Shared Property Culture As Global.System.Globalization.CultureInfo']
 strings={}
 for data in E.parse(path).iter('data'):
  assert not data.get('type') and not data.get('mimetype');field=data.get('name');assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',field)
  strings[field]=(data.findtext('value') or '').replace('\r\n','\n').replace('\n','\r\n')
  code.extend(['Friend Shared ReadOnly Property ['+field+'] As String','Get','Return Manager.GetString("'+field+'",Culture)','End Get','End Property'])
 code+=['End Class']+(['End Namespace'] if namespace else [])
 wrapper=folder/(cls+'.g.vb');wrapper.write_text('\n'.join(code)+'\n');E.SubElement(items,'Compile',Include=native(wrapper))
 neutral=folder/(cls+'.resx');write_resx(E.parse(path),neutral)
 E.SubElement(items,'EmbeddedResource',Include=native(neutral),LogicalName=cls+'.resources')
 localizations.append(dict(assembly=name,resource=cls,culture='',strings=strings))
 ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
 for translation in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
  xlf=E.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
  translated={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
  localized=E.parse(path)
  for data in localized.iter('data'):
   if data.get('name') in translated:data.find('value').text=translated[data.get('name')]
  target=folder/(cls+'.'+culture+'.resx');write_resx(localized,target)
  E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=cls+'.'+culture+'.resources',Culture=culture,WithCulture='true')
  localizations.append(dict(assembly=name,resource=cls,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))
E.indent(p);E.ElementTree(p).write(folder/'Library.vbproj',encoding='utf-8',xml_declaration=True)
manifest=dict(source_files=len(files),source_sha256={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},source_paths=[f.relative_to(source).as_posix() for f in sorted(files)],imports=[f.relative_to(source).as_posix() for f in sorted(visited)],resources={f.relative_to(source).as_posix():cls for f,cls in sorted(resources.items())},friends=friends,global_imports=sorted(imports),dependencies=deps)
(out/'source-items.json').write_text(json.dumps({name:manifest},indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
prefix=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
feed=subprocess.check_output(['cygpath','-am',str(prefix)],text=True).strip() if shutil.which('cygpath') else str(prefix)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
print('Prepared',len(files),'original sources;',len(localizations),'resource sets;',sum(len(e['strings']) for e in localizations),'resource strings')
