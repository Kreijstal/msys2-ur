"""Prepare full upstream StyleCop assemblies for the source-built .NET 8 host."""
from pathlib import Path
import hashlib,json,os,re,shutil,struct,subprocess,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:])
subprocess.run([sys.executable,str(Path(__file__).with_name('verify-source.py')),str(source)],check=True)
out.mkdir()
common=Path(os.path.commonpath([source,out]))
base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
key=(source/'build/keys/StyleCopAnalyzers.snk').read_bytes()
assert key[0]==7 and key[8:12]==b'RSA2'
size=struct.unpack_from('<I',key,12)[0]//8
blob=bytearray(key[:20+size]);blob[0]=6;blob[8:12]=b'RSA1'
public=struct.pack('<III',0x2400,0x8004,len(blob))+blob
(out/'Library.public.snk').write_bytes(public)
token=hashlib.sha1(public).digest()[-8:][::-1].hex();assert token=='cfeb5dbada5e1c25'
print('Public key token:',token)
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}:
  removed.append(f.relative_to(source).as_posix());f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
manifest={};resources=[]
baseline=source/'StyleCop.Analyzers/StyleCop.Analyzers/Lightup/.generated/StyleCop.Analyzers.CodeGeneration/StyleCop.Analyzers.CodeGeneration.SyntaxLightupGenerator'
wrappers=sorted(f.name.removesuffix('Wrapper.g.cs') for f in baseline.glob('*Wrapper.g.cs'))
assert wrappers and 'TupleElementSyntax' in wrappers and 'FileScopedNamespaceDeclarationSyntax' in wrappers
(out/'compatibility-wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
for name in ['StyleCop.Analyzers.CodeGeneration','StyleCop.Analyzers','StyleCop.Analyzers.CodeFixes']:
 folder=out/name;folder.mkdir();main=source/'StyleCop.Analyzers'/name
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace='StyleCop.Analyzers',Version='1.2.0-beta.556',AssemblyVersion='1.2.0.556',FileVersion='1.2.0.556',InformationalVersion='1.2.0-beta.556+73a46ae2e65e7870fefe35e2c4c12bb7152f4ec5',IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='12.0',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Library.public.snk'),NeutralLanguage='en-US',CopyLocalLockFileAssemblies='true',IsPackable='false',NoWarn='CS0618;SYSLIB0051;CS1591',EmitCompilerGeneratedFiles='true',CompilerGeneratedFilesOutputPath=native(folder/'generated'))
 for k,v in values.items():E.SubElement(props,k).text=v
 # Match the SDK's default exclusion of hidden directories. Upstream commits
 # preview generator output under Lightup/.generated; regenerate it below.
 items=E.SubElement(project,'ItemGroup');files=sorted(f for f in main.rglob('*.cs') if not any(p.startswith('.') for p in f.relative_to(main).parts));overlays=[]
 for f in files:
  compiled=f
  if name.endswith('CodeGeneration') and f.name=='SyntaxLightupGenerator.cs':
   # Existing source partials and SyntaxFactoryEx require these wrapper types
   # even when the newer compiler reference already exposes their syntax nodes.
   original=f.read_text(encoding='utf-8-sig')
   needle='this.ExistingType = compilationData.ExistingTypes.GetValueOrDefault'
   assert original.count(needle)==1
   replacement='this.ExistingType = (this.Name is '+' or '.join(json.dumps(n) for n in wrappers)+') ? null : compilationData.ExistingTypes.GetValueOrDefault'
   compiled=folder/f.name;compiled.write_text(original.replace(needle,replacement))
  elif name.endswith('CodeFixes') and f.name!='DocumentBasedFixAllProvider.cs':
   original=f.read_text(encoding='utf-8-sig')
   updated=re.sub(r'\bDocumentBasedFixAllProvider\b','global::StyleCop.Analyzers.Helpers.DocumentBasedFixAllProvider',original)
   if f.name=='SA1642SA1643CodeFixProvider.cs':
    assert updated.count('identifier.WithoutTrivia()')==2
    updated=updated.replace('identifier.WithoutTrivia()','global::StyleCop.Analyzers.Helpers.SpacingExtensions.WithoutTrivia(identifier)')
   if f.name=='SA1134CodeFixProvider.cs':
    needle='if (syntaxRoot.FindNode(diagnostic.Location.SourceSpan) is AttributeListSyntax)'
    assert updated.count(needle)==1
    updated=updated.replace(needle,'if (syntaxRoot.FindNode(diagnostic.Location.SourceSpan) is AttributeListSyntax attributeList && !attributeList.ContainsDiagnostics)')
    needle='var attributeListSyntax = (AttributeListSyntax)syntaxRoot.FindNode(diagnostic.Location.SourceSpan);'
    assert updated.count(needle)==1
    updated=updated.replace(needle,'var attributeListSyntax = syntaxRoot.FindNode(diagnostic.Location.SourceSpan) as AttributeListSyntax;\n            if (attributeListSyntax == null || attributeListSyntax.ContainsDiagnostics)\n            {\n                return;\n            }')
   if updated!=original:
    # A later Roslyn release added a type with the same name. Keep using the
    # original StyleCop implementation, including its Fix All behavior.
    compiled=folder/'overlays'/f.relative_to(main);compiled.parent.mkdir(parents=True,exist_ok=True)
    compiled.write_text(updated)
  E.SubElement(items,'Compile',Include=native(compiled))
  if compiled!=f:overlays.append(f.relative_to(source).as_posix())
 E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.9.2]')
 if name.endswith('CodeFixes'):
  E.SubElement(items,'ProjectReference',Include=native(out/'StyleCop.Analyzers/Library.csproj'))
  E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.9.2]')
 if name=='StyleCop.Analyzers':
  E.SubElement(items,'ProjectReference',Include=native(out/'StyleCop.Analyzers.CodeGeneration/Library.csproj'),OutputItemType='Analyzer',ReferenceOutputAssembly='false')
  for filename in ['OperationInterfaces.xml','Syntax.xml']:
   E.SubElement(items,'AdditionalFiles',Include=native(main/'Lightup'/filename))
 for f in sorted(main.rglob('*.resx')):
  relative=f.relative_to(main);culture=''
  if '.' in f.stem:culture=f.stem.split('.',1)[1]
  cls='StyleCop.Analyzers.'+'.'.join(relative.parts[:-1])+'.'+f.stem.split('.')[0]
  strings={e.get('name'):e.findtext('value') or '' for e in E.parse(f).iter('data')}
  if not culture:
   namespace,_,leaf=cls.rpartition('.')
   code=['#nullable enable',f'namespace {namespace} {{ internal static class {leaf} {{',f'internal static System.Resources.ResourceManager ResourceManager {{get;}} = new System.Resources.ResourceManager({json.dumps(cls)},typeof({leaf}).Assembly);','internal static System.Globalization.CultureInfo? Culture {get;set;}']
   for key in strings:
    identifier=re.sub(r'[^A-Za-z0-9_]','_',key);assert identifier.isidentifier(),key
    code.append(f'internal static string {identifier} => ResourceManager.GetString({json.dumps(key)},Culture)!;')
   code.append('}}');generated=folder/(cls+'.g.cs');generated.write_text('\n'.join(code)+'\n')
   E.SubElement(items,'Compile',Include=native(generated))
  E.SubElement(items,'EmbeddedResource',Include=native(f),LogicalName=cls+('.'+culture if culture else '')+'.resources',**(dict(Culture=culture,WithCulture='true') if culture else {}))
  resources.append(dict(assembly=name,resource=cls,culture=culture,strings=strings))
 E.indent(project);E.ElementTree(project).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
 manifest[name]=dict(source_files=len(files),resources=sum(e['assembly']==name for e in resources),overlays=overlays)
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'localization.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
prefix=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
feed=subprocess.check_output(['cygpath','-am',str(prefix)],text=True).strip() if shutil.which('cygpath') else str(prefix)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
