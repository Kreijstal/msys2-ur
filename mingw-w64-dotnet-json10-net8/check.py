"""Fresh exact-source NuGet restore, original API/metadata and runtime consumers."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E,zipfile
root,out,check=(Path(p).resolve() for p in sys.argv[1:4]);feed=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else out/'feed'
assert not check.exists();check.mkdir();here=Path(__file__).resolve().parent
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
 p=Path(p).resolve()
 if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
 return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['System.Text.Encodings.Web','System.IO.Pipelines','System.Text.Json']
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',AssemblyName='Check',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='preview',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd',EmitCompilerGeneratedFiles='true',CompilerGeneratedFilesOutputPath='generated').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
for p in sorted((here/'inputs').glob('*.cs')):
 if p.name not in {'Program.cs','CheckApi.cs'}:continue
 E.SubElement(items,'Compile',Include=native(p))
for name in names:E.SubElement(items,'PackageReference',Include=name,Version='[10.0.5]')
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.14.0]')
E.indent(tree);E.ElementTree(tree).write(check/'Build.csproj',encoding='utf-8',xml_declaration=True)
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
for i,p in enumerate(dict.fromkeys([feed,Path('/clang64/lib/dotnet/library-packs')])):E.SubElement(sources,'add',key='source'+str(i),value=native(p))
E.ElementTree(config).write(check/'NuGet.config',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_CLI_HOME=native(check/'cli-home'),NUGET_PACKAGES=native(check/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false');dotnet='/clang64/lib/dotnet/dotnet.exe'
with (check/'build.log').open('w') as log:subprocess.run([dotnet,'build',native(check/'Build.csproj'),'-c','Release','--configfile',native(check/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assets=json.loads((check/'obj/project.assets.json').read_text());target=next(iter(assets['targets'].values()));packages={p.name.lower():p for folder in [Path('/clang64/lib/dotnet/library-packs'),feed] for p in folder.glob('*.nupkg')};actual={}
for ident,item in assets['libraries'].items():
 if item['type']!='package':continue
 name,version=ident.split('/');filename=name.lower()+'.'+version+'.nupkg';package=packages[filename]
 assert (check/'cache'/item['path']/filename).read_bytes()==package.read_bytes(),ident
 with zipfile.ZipFile(package) as z:
  for path in z.namelist():
   if path.endswith('.dll'):assert (check/'cache'/item['path']/path).read_bytes()==z.read(path),(ident,path)
  if name in names:
   assert set(target[ident]['compile'])==set(target[ident]['runtime'])=={'lib/net8.0/'+name+'.dll'},(ident,target[ident])
   assert (check/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==z.read('lib/net8.0/'+name+'.dll')==(out/name/'bin/Release/net8.0'/(name+'.dll')).read_bytes(),name
 actual[ident]=sha(package)
assert any((check/'generated').rglob('*JsonContext*')) or any((check/'generated').rglob('*SourceContext*')),'Original JSON source generator output absent'
refs=Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')
command=[dotnet,native(check/'bin/Release/net8.0/Check.dll'),native(root/'r'),native(out/'localization.json'),native(refs),native(check/'runtime-results.json')]
with (check/'run.log').open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
(check/'run.exit').write_text(str(r.returncode)+'\n');assert r.returncode==0,(r.returncode,check/'run.log')
result=json.loads((check/'runtime-results.json').read_text());result.update(command=command,exit_code=0,formal_pacman_installed=feed==Path('/clang64/lib/dotnet/library-packs'),all_restored_source_archive_and_dll_bytes_verified=True,source_package_sha256=actual)
(check/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS exact NET8 JSON10/encoder/pipelines source-package consumer and original API/metadata/runtime contracts')
