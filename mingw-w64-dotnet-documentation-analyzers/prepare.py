from pathlib import Path
import hashlib,json,os,re,shutil,struct,subprocess,sys
import xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
inputs=Path(__file__).parent
common=Path(os.path.commonpath([source,out]));base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
key=(source/'build/keys/DocumentationAnalyzers.dev.snk').read_bytes();assert key[0]==7 and key[8:12]==b'RSA2'
size=struct.unpack_from('<I',key,12)[0]//8;blob=bytearray(key[:20+size]);blob[0]=6;blob[8:12]=b'RSA1';public=struct.pack('<III',0x2400,0x8004,len(blob))+blob
assert hashlib.sha1(public).digest()[-8:][::-1].hex()=='2bc5e20c3ad68793'
(out/'Library.public.snk').write_bytes(public)
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}:
  removed.append(f.relative_to(source).as_posix());f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
resources=[];manifest={}
for name in ['DocumentationAnalyzers','DocumentationAnalyzers.CodeFixes']:
 folder=out/name;folder.mkdir();main=source/'DocumentationAnalyzers'/name
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace='DocumentationAnalyzers',Version='1.0.0-beta.59',AssemblyVersion='1.0.0.59',FileVersion='1.0.0.59',InformationalVersion='1.0.0-beta.59+489c06575beee224030ffdc9e91ce43569f32a79',IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',LangVersion='12.0',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile=native(out/'Library.public.snk'),DefineConstants='$(DefineConstants);DEVELOPMENT_KEY',NeutralLanguage='en-US',CopyLocalLockFileAssemblies='true',IsPackable='false',NoWarn='CS0618;SYSLIB0051')
 for k,v in values.items():E.SubElement(props,k).text=v
 items=E.SubElement(project,'ItemGroup')
 files=sorted(main.rglob('*.cs'))
 for f in files:E.SubElement(items,'Compile',Include=native(f))
 E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.9.2]')
 if name.endswith('CodeFixes'):
  E.SubElement(items,'ProjectReference',Include=native(out/'DocumentationAnalyzers/Library.csproj'))
  E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.9.2]')
  E.SubElement(items,'PackageReference',Include='CommonMark.NET',Version='[0.15.1]')
 for f in sorted(main.rglob('*.resx')):
  designer=f.with_suffix('.Designer.cs');assert designer.is_file(),f
  logical=re.search(r'ResourceManager\("([^"]+)"',designer.read_text(encoding='utf-8-sig'))[1]
  E.SubElement(items,'EmbeddedResource',Include=native(f),LogicalName=logical+'.resources')
  resources.append(dict(assembly=name,resource=logical,strings={e.get('name'):e.findtext('value') or '' for e in E.parse(f).iter('data')}))
 E.indent(project);E.ElementTree(project).write(folder/'Library.csproj',encoding='utf-8',xml_declaration=True)
 manifest[name]=dict(source_files=len(files),resources=[e['resource'] for e in resources if e['assembly']==name])
(out/'source-items.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'localization.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
installed=Path(os.environ.get('MINGW_PREFIX','/clang64'))/'lib/dotnet/library-packs'
installed_native=subprocess.check_output(['cygpath','-am',str(installed)],text=True).strip() if shutil.which('cygpath') else str(installed)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+installed_native+'"/></packageSources></configuration>\n')

for tool,filename,roslyn in [('fixture-tool','ExtractFixtures.cs',True),('inventory-tool','InspectInventory.cs',False)]:
 folder=out/tool;folder.mkdir();shutil.copyfile(inputs/filename,folder/'Program.cs')
 project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(props,k).text=v
 if roslyn:E.SubElement(E.SubElement(project,'ItemGroup'),'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.9.2]')
 E.indent(project);E.ElementTree(project).write(folder/'Tool.csproj',encoding='utf-8',xml_declaration=True)
shutil.copyfile(inputs/'ExpectedInventory.json',out/'ExpectedInventory.json')
