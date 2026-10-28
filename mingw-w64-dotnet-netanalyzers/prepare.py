"""Build the complete SDK-selected .NET Core/CSharp/VisualBasic analyzer and code-fix projects."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
import xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
inputs=Path(__file__).parent
common=Path(os.path.commonpath([source,out]));base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
def tag(e):return e.tag.rsplit('}',1)[-1]
# Use the upstream production Microsoft shared public identity, not the private test key.
key=bytes.fromhex((inputs/'MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Analyzer.public.snk').write_bytes(key)
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}:
  removed.append(dict(path=f.relative_to(source).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()));f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
manifest={};resources=[]
for language,name in [('Core','Microsoft.CodeAnalysis.NetAnalyzers'),('CSharp','Microsoft.CodeAnalysis.CSharp.NetAnalyzers'),('VisualBasic','Microsoft.CodeAnalysis.VisualBasic.NetAnalyzers')]:
 vb=language=='VisualBasic';ext='.vb' if vb else '.cs';folder=out/name;folder.mkdir();main=source/'src/NetAnalyzers'/language
 original=main/(name+ext+'proj');tree=E.parse(original)
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace='',Version='8.0.0-preview.26274.2',AssemblyVersion='8.0.14.27402',FileVersion='8.0.14.27402',InformationalVersion='8.0.0-preview.26274.2+0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4',IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',RunAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='16' if vb else '12.0',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Analyzer.public.snk'),CopyLocalLockFileAssemblies='true',IsPackable='false',DefineConstants='NET_ANALYZERS,CODEANALYSIS_V3_OR_BETTER,CODEANALYSIS_V3_7_OR_BETTER,HAS_IOPERATION' if vb else 'NET_ANALYZERS;CODEANALYSIS_V3_OR_BETTER;CODEANALYSIS_V3_7_OR_BETTER;HAS_IOPERATION',NoWarn='CS0436;CS0618;SYSLIB0051;SYSLIB0050',DotNetBuildFromSource='true')
 for k,v in values.items():E.SubElement(props,k).text=v
 items=E.SubElement(project,'ItemGroup')
 files={f.resolve() for f in main.rglob('*'+ext)};embedded=set(main.rglob('*.resx'));visited=set();friends=[]
 def collect(path):
  if path in visited:return
  visited.add(path);root=E.parse(path).getroot()
  for group in root:
   if tag(group)=='Import':
    relative=group.get('Project');assert '$(' not in relative;collect((path.parent/relative.replace('\\','/')).resolve())
   elif tag(group)=='ItemGroup':
    condition=group.get('Condition')
    assert condition in {None,"'$(HasIOperation)' == 'true'","'$(ExcludeInternalFlowAnalyses)' != 'true'","'$(IsTestProject)' != 'true' and '$(NonShipping)' != 'true'"},(path,condition)
    for e in group:
     kind=tag(e)
     if kind=='Compile' and e.get('Include'):
      assert not e.get('Condition');relative=e.get('Include').replace('$(MSBuildThisFileDirectory)',str(path.parent)+'/').replace('\\','/')
      assert '$(' not in relative and '*' not in relative;files.add((path.parent/relative).resolve())
     elif kind=='EmbeddedResource' and e.get('Include'):
      relative=e.get('Include').replace('$(MSBuildThisFileDirectory)',str(path.parent)+'/').replace('\\','/')
      assert '$(' not in relative;embedded.add((path.parent/relative).resolve())
     elif kind=='InternalsVisibleTo':friends.append(e.get('Include')+', PublicKey='+key.hex())
 collect(original)
 substitutions={}
 for file in sorted(files):
  assert file.is_file(),file;compile_file=file
  ports={
   'TypesThatOwnDisposableFieldsShouldBeDisposable.cs': [('disposableFieldNamesBuilder.AsEnumerable_NonConcurrent().Order()', 'Analyzer.Utilities.Extensions.IEnumerableExtensions.Order(disposableFieldNamesBuilder.AsEnumerable_NonConcurrent())')],
   'GlobalFlowStateAnalysisValueSet.cs': [('parentsBuilder.Order()', 'Analyzer.Utilities.Extensions.IEnumerableExtensions.Order(parentsBuilder)'), ('AnalysisValues.Select(f => f.ToString()).Order()', 'Analyzer.Utilities.Extensions.IEnumerableExtensions.Order(AnalysisValues.Select(f => f.ToString()))')],
   'CSharpUseStringMethodCharOverloadWithSingleCharacters.Fixer.cs': [('SyntaxFactory.SeparatedList(arguments)', 'SyntaxFactory.SeparatedList(arguments.Cast<ArgumentSyntax>())')],
   'DoNotPassLiteralsAsLocalizedParameters.cs': [('literalValues.Order()', 'Analyzer.Utilities.Extensions.IEnumerableExtensions.Order(literalValues)')]}
  if file.name in ports:
   raw=file.read_text(encoding='utf-8-sig')
   for old,new in ports[file.name]:assert raw.count(old)==1;raw=raw.replace(old,new)
   compile_file=folder/(file.stem+'.port'+file.suffix);compile_file.write_text(raw)
   substitutions[file.relative_to(source).as_posix()]=dict(reason=('Preserve CSharp argument-node types when calling the newer SyntaxGenerator API' if file.name=='CSharpUseStringMethodCharOverloadWithSingleCharacters.Fixer.cs' else 'Qualify original helper calls against the newer .NET Enumerable.Order extension; preserve original ordering implementation'),changes=ports[file.name],sha256=hashlib.sha256(compile_file.read_bytes()).hexdigest())
  E.SubElement(items,'Compile',Include=native(compile_file))
 if language=='Core':
  for dep in ['Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.Workspaces.Common']:E.SubElement(items,'PackageReference',Include=dep,Version='[4.9.2]')
 else:
  E.SubElement(items,'ProjectReference',Include=native(out/'Microsoft.CodeAnalysis.NetAnalyzers/Library.csproj'))
  E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.'+language+'.Workspaces',Version='[4.9.2]')
 for tracking in ['AnalyzerReleases.Shipped.md','AnalyzerReleases.Unshipped.md']:
  E.SubElement(items,'None',Include=native(main/tracking),Link='AnalyzerReleases/'+name+'/'+tracking,CopyToOutputDirectory='PreserveNewest')
 attributes=folder/('Friends.g'+ext)
 attributes.write_text('\n'.join(('<Assembly: Global.System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(f)+')>') if vb else ('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(f)+')]') for f in friends)+'\n')
 E.SubElement(items,'Compile',Include=native(attributes))
 for path in sorted(embedded):
  logical=path.parent.name+'.'+path.stem
  if path.suffix!='.resx':
   target=folder/path.name;target.write_bytes(path.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
   E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=logical+path.suffix);continue
  assert not vb,'VB resource wrappers require a VB generator'
  leaf=path.stem;namespace=logical.rsplit('.',1)[0];code=['#nullable enable','namespace '+namespace+' { internal partial class '+leaf+' {','internal static System.Resources.ResourceManager ResourceManager {get;} = new System.Resources.ResourceManager('+json.dumps(logical)+',typeof('+leaf+').Assembly);','internal static System.Globalization.CultureInfo? Culture {get;set;}']
  strings={}
  for entry in E.parse(path).iter('data'):
   assert not entry.get('type') and not entry.get('mimetype');field=entry.get('name');assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',field)
   strings[field]=(entry.findtext('value') or '').replace('\r\n','\n').replace('\n','\r\n')
   code.append('internal static string @'+field+' => ResourceManager.GetString('+json.dumps(field)+',Culture)!;')
  code.append('}}');wrapper=folder/(leaf+'.g.cs');wrapper.write_text('\n'.join(code)+'\n');E.SubElement(items,'Compile',Include=native(wrapper))
  def write_resx(tree,target):
   for data in tree.iter('data'):
    v=data.find('value')
    if v is not None:v.text=(v.text or '').replace('\r\n','\n').replace('\n','\r\n')
   target.write_bytes(E.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True).replace(b'\r',b'&#13;'))
  neutral=folder/path.name;write_resx(E.parse(path),neutral);E.SubElement(items,'EmbeddedResource',Include=native(neutral),LogicalName=logical+'.resources')
  resources.append(dict(assembly=name,resource=logical,culture='',strings=strings))
  ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
  for translation in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
   xlf=E.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
   translated={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in xlf.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
   localized=E.parse(path)
   for data in localized.iter('data'):
    if data.get('name') in translated:data.find('value').text=translated[data.get('name')]
   target=folder/(leaf+'.'+culture+'.resx');write_resx(localized,target)
   E.SubElement(items,'EmbeddedResource',Include=native(target),LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
   resources.append(dict(assembly=name,resource=logical,culture=culture,strings={e.get('name'):e.findtext('value') or '' for e in localized.iter('data')}))
 E.indent(project);E.ElementTree(project).write(folder/('Library.vbproj' if vb else 'Library.csproj'),encoding='utf-8',xml_declaration=True)
 manifest[name]=dict(source_substitutions=substitutions,source_files=len(files),source_paths=[f.relative_to(source).as_posix() for f in sorted(files)],source_sha256={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},imports=[f.relative_to(source).as_posix() for f in sorted(visited)],embedded=[f.relative_to(source).as_posix() for f in sorted(embedded)],friends=friends)
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'localization.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
installed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
feed=subprocess.check_output(['cygpath','-am',str(installed)],text=True).strip() if shutil.which('cygpath') else str(installed)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')

main=source/'src/Tools/GenerateDocumentationAndConfigFiles';folder=out/'config-tool';folder.mkdir()
files=set(main.glob('*.cs'))
for e in E.parse(main/'GenerateDocumentationAndConfigFiles.csproj').iter('Compile'):files.add((main/e.get('Include').replace('\\','/')).resolve())
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='12.0',NoWarn='CS0436;CS0618;SYSLIB0050;SYSLIB0051').items():E.SubElement(props,k).text=v
items=E.SubElement(project,'ItemGroup')
for f in sorted(files):assert f.is_file();E.SubElement(items,'Compile',Include=native(f))
for dep in ['Microsoft.CodeAnalysis.CSharp.Workspaces','Microsoft.CodeAnalysis.VisualBasic.Workspaces']:E.SubElement(items,'PackageReference',Include=dep,Version='[4.9.2]')
E.indent(project);E.ElementTree(project).write(folder/'Tool.csproj',encoding='utf-8',xml_declaration=True)
manifest['config-generator']=dict(imports=[(main/'GenerateDocumentationAndConfigFiles.csproj').relative_to(source).as_posix()],source_files=len(files),source_paths=[f.relative_to(source).as_posix() for f in sorted(files)],source_sha256={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)})
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared complete original .NET analyzer inputs:',{name:entry['source_files'] for name,entry in manifest.items()})
