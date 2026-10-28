from pathlib import Path
import os,sys,subprocess,json,hashlib,re,xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
common=Path(os.path.commonpath([source,out]));base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip()
def native(p):return base+'/'+Path(p).resolve().relative_to(common).as_posix()
settings=E.parse(source/'eng/targets/Settings.props')
def public_key(name):
 value=next(e.text for e in settings.iter(name));seen={name}
 while re.fullmatch(r'\$\((\w+)\)',value):
  name=value[2:-1];assert name not in seen;seen.add(name);value=next(e.text for e in settings.iter(name))
 assert re.fullmatch('[0-9a-fA-F]+',value);return value
key=public_key('MicrosoftSharedPublicKey');(out/'Compiler.public.snk').write_bytes(bytes.fromhex(key))
assert hashlib.sha1(bytes.fromhex(key)).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib'}:
  removed.append(dict(path=f.relative_to(source).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()));f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
manifest={}
for name in ['Microsoft.CodeAnalysis.ExternalAccess.RazorCompiler','csc']:
 folder=out/name;folder.mkdir();project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',OutputType='Exe' if name=='csc' else 'Library',AssemblyName=name,RootNamespace=name,UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='12.0',AllowUnsafeBlocks='true',Version='4.9.2',AssemblyVersion='4.9.0.0',FileVersion='4.9.2.0',InformationalVersion='4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',IncludeSourceRevisionInInformationalVersion='false',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Compiler.public.snk'),ServerGarbageCollection='true').items():E.SubElement(props,k).text=v
 files=[]
 items=E.SubElement(project,'ItemGroup');E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.Common',Version='[4.9.2]')
 if name=='csc':
  E.SubElement(props,'StartupObject').text='Microsoft.CodeAnalysis.CSharp.CommandLine.Program'
  E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.9.2]')
  E.SubElement(items,'ProjectReference',Include=native(out/'Microsoft.CodeAnalysis.ExternalAccess.RazorCompiler/Tool.csproj'))
  original=E.parse(source/'src/Compilers/CSharp/csc/CscCommandLine.projitems')
  shared=source/'src/Compilers/CSharp/csc/CscCommandLine.projitems';tree=E.parse(shared)
  for entry in tree.findall('.//{*}Compile'):
   path=entry.get('Include').replace('$(MSBuildThisFileDirectory)',str(shared.parent)+'/').replace('\\','/');assert '$(' not in path
   E.SubElement(items,'Compile',Include=native(path));files.append(Path(path).resolve().relative_to(source).as_posix())
 else:
  main=source/'src/Tools/ExternalAccess/RazorCompiler'
  original=E.parse(main/'Microsoft.CodeAnalysis.ExternalAccess.RazorCompiler.csproj')
  for path in main.rglob('*.cs'):E.SubElement(items,'Compile',Include=native(path));files.append(Path(path).resolve().relative_to(source).as_posix())
 declarations=[]
 for friend in original.findall('.//{*}InternalsVisibleTo'):
  variable=friend.get('Key');value=public_key(variable[2:-1]) if variable else key
  declarations.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(friend.get('Include')+', PublicKey='+value)+')]')
 (folder/'Friends.g.cs').write_text('\n'.join(declarations)+'\n');E.SubElement(items,'Compile',Include=native(folder/'Friends.g.cs'))
 manifest[name]=dict(source_files=sorted(files),friend_declarations=declarations)
 E.indent(project);E.ElementTree(project).write(folder/'Tool.csproj',encoding='utf-8',xml_declaration=True)
feed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
feed_native=subprocess.check_output(['cygpath','-am',str(feed)],text=True).strip()
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='installed',value=feed_native)
E.indent(config);E.ElementTree(config).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n')
