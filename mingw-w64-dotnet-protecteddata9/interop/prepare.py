"""Prepare complete source9.0.11 interop generators on the source NET8 bootstrap host."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
assert sha(archive)=='63ab12fafdec8559d59d25e21ddaf0edbde90d6c538b44d4cbb6f693a61e90df'
source=out/'r';source.mkdir();extracted={}
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile():continue
  n=m.name.partition('/')[2]
  if not (n.startswith(('src/libraries/System.Runtime.InteropServices/gen/','src/libraries/System.Private.CoreLib/src/','src/libraries/Common/src/')) or n=='src/libraries/System.Runtime.InteropServices/tests/Common/MarshalDirection.cs' or n in {'LICENSE.TXT','src/libraries/Directory.Build.targets'}):continue
  p=source/n;p.parent.mkdir(parents=True,exist_ok=True);data=t.extractfile(m).read();assert not data.startswith(b'MZ'),n;p.write_bytes(data);extracted[n]=hashlib.sha256(data).hexdigest()
libs=source/'src/libraries';interop=libs/'System.Runtime.InteropServices/gen';models={}
for assembly,directory in [('Microsoft.Interop.SourceGeneration','Microsoft.Interop.SourceGeneration'),('Microsoft.Interop.LibraryImportGenerator','LibraryImportGenerator')]:
 original=interop/directory/(directory+'.csproj');folder=out/assembly;folder.mkdir();tree=E.parse(original);root=tree.getroot();root.attrib.pop('Sdk')
 for parent in root.iter():
  for item in list(parent):
   if item.tag in {'PackageReference','ProjectReference'}:parent.remove(item);continue
   if item.tag=='TargetFramework':item.text='net8.0'
   if item.tag in {'Compile','EmbeddedResource'}:
    for attr in ['Include','Remove','Update']:
     value=item.get(attr,'').replace('\\','/')
     if value and '$(' not in value:item.set(attr,native(original.parent/value))
 E.ElementTree(root).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
 wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',AssemblyName=assembly,RootNamespace='Microsoft.Interop',EnableDefaultItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',CommonPath=native(libs/'Common/src')+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/',AllowUnsafeBlocks='true',Nullable='enable',LangVersion='13.0',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',CopyLocalLockFileAssemblies='true',CscToolPath=native(prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'),CscToolExe='csc53.cmd',Version='9.0.11',AssemblyVersion='9.0.0.0',InformationalVersion='9.0.11+fa7cdded37981a97cec9a3e233c4a6af58a91c57').items():E.SubElement(pg,k).text=v
 E.SubElement(wrapper,'Import',Project='upstream.proj');items=E.SubElement(wrapper,'ItemGroup')
 files=list(original.parent.rglob('*.cs'))
 for p in files:E.SubElement(items,'Compile',Include=native(p))
 E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp.Workspaces',Version='[4.9.2]')
 if directory=='LibraryImportGenerator':E.SubElement(items,'ProjectReference',Include=native(out/'Microsoft.Interop.SourceGeneration/Microsoft.Interop.SourceGeneration.csproj'))
 resource=interop/'Common/Resources/Strings.resx';logical='FxResources.'+assembly+'.SR';sr=folder/'SR.Generated.cs';code=['#nullable enable','namespace FxResources.'+assembly+' { internal static class SR {} }','namespace System {internal static partial class SR { internal static global::System.Resources.ResourceManager ResourceManager {get;}=new global::System.Resources.ResourceManager("'+logical+'",typeof(FxResources.'+assembly+'.SR).Assembly);']
 for e in E.parse(resource).iter('data'):code.append('internal static string @'+e.get('name')+' => GetResourceString('+json.dumps(e.get('name'))+');')
 code.append('}}');sr.write_text('\n'.join(code)+'\n',encoding='utf-8')
 for p in [sr,libs/'Common/src/System/SR.cs']:E.SubElement(items,'Compile',Include=native(p))
 E.SubElement(items,'EmbeddedResource',Include=native(resource),LogicalName=logical+'.resources')
 capture=E.SubElement(wrapper,'Target',Name='CaptureInputs',BeforeTargets='CoreCompile')
 for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
 E.ElementTree(wrapper).write(folder/(assembly+'.csproj'),encoding='utf-8',xml_declaration=True)
 models[assembly]=dict(original_project_sha256=sha(original),default_cs_sha256={p.relative_to(source).as_posix():sha(p) for p in files},original_target='netstandard2.0',bootstrap_target='net8.0',original_roslyn_package_property='MicrosoftCodeAnalysisVersion_LatestVS',bootstrap_source_roslyn_package='4.9.2',full_original_profiles_built=False)
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='installed-source',value=native(prefix/'lib/dotnet/library-packs'));E.ElementTree(config).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57',source_archive_sha256=sha(archive),extracted_source_sha256=extracted,projects=models,full_original_netstandard_generator_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8');print('Prepared two complete original interop generator source projects for NET8 bootstrap')
