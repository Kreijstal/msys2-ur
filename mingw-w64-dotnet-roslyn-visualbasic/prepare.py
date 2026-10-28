"""Build the complete VB compiler and its original generators against source .NET 8."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
common=Path(os.path.commonpath([source,out]))
base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
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
for p in source.rglob('*'):
 if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}:
  removed.append(dict(path=p.relative_to(source).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()));p.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
manifest={};localizations=[]
def project(name,vb=True,executable=False):
 folder=out/name;folder.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,OutputType='Exe' if executable else 'Library',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',GenerateDocumentationFile='false',Version='4.9.2',AssemblyVersion='4.9.0.0',FileVersion='4.9.2.0',InformationalVersion='4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',IncludeSourceRevisionInInformationalVersion='false')
 if vb:values.update(RootNamespace='',LangVersion='latest',VBRuntime='Embed',MyType='Empty',OptionExplicit='On',OptionInfer='On',OptionCompare='Binary',RemoveIntegerChecks='true',NoWarn='40057;42014')
 else:values.update(LangVersion='12.0',Nullable='enable')
 for k,v in values.items():E.SubElement(props,k).text=v
 items=E.SubElement(p,'ItemGroup')
 if vb:
  for name in ['Microsoft.VisualBasic','System','System.Collections','System.Collections.Generic','System.Diagnostics','System.Linq']:E.SubElement(items,'Import',Include=name)
  # Preserve upstream eng/targets/Imports.targets: WorkAroundDotnetSdk10591.
  target=E.SubElement(p,'Target',Name='RemoveEmbeddedVbRuntimeReferences',AfterTargets='ResolveTargetingPackAssets')
  E.SubElement(E.SubElement(target,'ItemGroup'),'Reference',Remove='@(Reference)',Condition="'%(FileName)' == 'Microsoft.VisualBasic' or '%(FileName)' == 'Microsoft.VisualBasic.Core'")
 return folder,p,props,items
def save(folder,p,vb=True):
 E.indent(p);E.ElementTree(p).write(folder/('Library.vbproj' if vb else 'Library.csproj'),encoding='utf-8',xml_declaration=True)
tools=source/'src/Tools/Source/CompilerGeneratorTools/Source'
for name,upstream,vb in [('VBSyntaxGenerator','VisualBasicSyntaxGenerator',True),('VBErrorFactsGenerator','VisualBasicErrorFactsGenerator',True),('BoundTreeGenerator','BoundTreeGenerator',False)]:
 folder,p,props,items=project(name,vb,True);files=sorted((tools/upstream).rglob('*.vb' if vb else '*.cs'))
 if vb:
  E.SubElement(props,'RootNamespace').text='Microsoft.CodeAnalysis.VisualBasic.Internal.'+name
 if name=='VBSyntaxGenerator':
  E.SubElement(props,'OptionStrict').text='Off'
  E.SubElement(props,'StartupObject').text='Microsoft.CodeAnalysis.VisualBasic.Internal.VBSyntaxGenerator.Program'
  files.extend(source/'src/Compilers/VisualBasic/Portable'/r for r in ['Declarations/DeclarationModifiers.vb','Syntax/SyntaxKind.vb'])
  for ns in ['System.Collections.ObjectModel','System.Xml.Linq']:E.SubElement(items,'Import',Include=ns)
  E.SubElement(items,'EmbeddedResource',Include=native(tools/upstream/'VBSyntaxModelSchema.xsd'),LogicalName='VBSyntaxModelSchema.xsd')
 for f in files:E.SubElement(items,'Compile',Include=native(f))
 manifest[name]=dict(source_files=len(files));save(folder,p,vb)

name='Microsoft.CodeAnalysis.VisualBasic';folder,p,props,items=project(name)
for k,v in dict(SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Roslyn.public.snk'),PackageId=name,PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/roslyn',RepositoryCommit='9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',PackageReadmeFile='README.md',ProduceReferenceAssembly='true').items():E.SubElement(props,k).text=v
E.SubElement(items,'None',Include=native(Path(__file__).with_name('README.md')),Pack='true',PackagePath='/')
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.Common',Version='[4.9.2]')
for alias in ['IdentifierComparison = Microsoft.CodeAnalysis.CaseInsensitiveComparison','Roslyn.Utilities']:E.SubElement(items,'Import',Include=alias)
main=source/'src/Compilers/VisualBasic/Portable'
embedded=['Embedded.vb','InternalXmlHelper.vb','VbCoreSourceText.vb','VbMyTemplateText.vb']
excluded={main/'Symbols/EmbeddedSymbols'/n for n in embedded}
files=sorted(f for f in main.rglob('*.vb') if f not in excluded and f.relative_to(main).parts[0]!='Generated')
files.append(source/'src/Compilers/VisualBasic/BasicAnalyzerDriver/VisualBasicDeclarationComputer.vb')
for f in files:E.SubElement(items,'Compile',Include=native(f))
E.SubElement(items,'Compile',Include=native(out/'generated')+'/*.vb')
for filename in embedded:
 # Match Windows checkout line endings used by the published Windows build,
 # while deriving every embedded byte from the pinned text sources.
 target=folder/filename;raw=(main/'Symbols/EmbeddedSymbols'/filename).read_bytes()
 target.write_bytes(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
 E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=filename)
original=E.parse(main/(name+'.vbproj'))
friends=[]
for f in original.iter('InternalsVisibleTo'):
 public=f.get('Key');public=key_value(public[2:-1]) if public else key.hex()
 friends.append(f.get('Include')+', PublicKey='+public)
attributes=['<Assembly: Global.System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(f)+')>' for f in friends]
attributes.append('<Assembly: Global.Microsoft.CodeAnalysis.CommitHash("9934fb9e3527e1c0c51314e57d4aab30f97e8f9e")>')
attrs=folder/'Friends.g.vb';attrs.write_text('\n'.join(attributes)+'\n');E.SubElement(items,'Compile',Include=native(attrs))
resx=main/'VBResources.resx';logical='Microsoft.CodeAnalysis.VisualBasic.VBResources'
code=['Namespace Microsoft.CodeAnalysis.VisualBasic','Friend NotInheritable Class VBResources','Private Sub New()','End Sub','Private Shared ReadOnly Manager As New Global.System.Resources.ResourceManager("'+logical+'", GetType(VBResources).Assembly)','Friend Shared ReadOnly Property ResourceManager As Global.System.Resources.ResourceManager','Get','Return Manager','End Get','End Property','Friend Shared Property Culture As Global.System.Globalization.CultureInfo']
strings={}
for entry in E.parse(resx).iter('data'):
 assert not entry.get('type') and not entry.get('mimetype');field=entry.get('name');assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',field),field
 strings[field]=(entry.findtext('value') or '').replace('\r\n','\n').replace('\n','\r\n')
 code.extend(['Friend Shared ReadOnly Property ['+field+'] As String','Get','Return Manager.GetString("'+field+'", Culture)','End Get','End Property'])
code.extend(['End Class','End Namespace']);wrapper=folder/'VBResources.g.vb';wrapper.write_text('\n'.join(code)+'\n');E.SubElement(items,'Compile',Include=native(wrapper))
def windows_resource(tree,target):
 for data in tree.iter('data'):
  value=data.find('value')
  if value is not None:value.text=(value.text or '').replace('\r\n','\n').replace('\n','\r\n')
 # XML character references preserve CR characters through XML normalization.
 target.write_bytes(E.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True).replace(b'\r',b'&#13;'))
neutral=folder/'VBResources.resx';windows_resource(E.parse(resx),neutral)
E.SubElement(items,'EmbeddedResource',Include=native(neutral),LogicalName=logical+'.resources')
localizations.append(dict(assembly=name,resource=logical,culture='',strings=strings))
ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
for path in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
 xlf=E.parse(path);culture=xlf.find('x:file',ns).get('target-language')
 values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
 localized=E.parse(resx)
 for data in localized.iter('data'):
  if data.get('name') in values:data.find('value').text=values[data.get('name')]
 target=folder/(resx.stem+'.'+culture+'.resx');windows_resource(localized,target)
 E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
 localizations.append(dict(assembly=name,resource=logical,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))
manifest[name]=dict(source_files=len(files),generated_files=5,embedded_sources=embedded,friends=friends)
save(folder,p)
prefix=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
feed=subprocess.check_output(['cygpath','-am',str(prefix)],text=True).strip() if shutil.which('cygpath') else str(prefix)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
