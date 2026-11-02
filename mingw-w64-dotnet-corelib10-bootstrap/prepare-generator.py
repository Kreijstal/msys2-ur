"""Build exactly the original Standard2.0 CoreLib generator with source Roslyn4.14."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();source=root/'r';folder=root/'corelib10-1/generator';folder.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
original=source/'src/libraries/System.Private.CoreLib/gen/System.Private.CoreLib.Generators.csproj';upstream=E.parse(original);assert upstream.findtext('.//TargetFramework')=='netstandard2.0'
key='MicrosoftCodeAnalysisVersion_LatestVS';version=E.parse(source/'eng/Versions.props').findtext('.//'+key);assert version=='4.14.0',version
inputs=[]
for item in upstream.iter('Compile'):
 text=item.get('Include').replace('\\','/').replace('$(CoreLibSharedDir)',str(source/'src/libraries/System.Private.CoreLib/src')+'/')
 p=(Path(text) if Path(text).is_absolute() else original.parent/text).resolve();assert p.is_file();inputs.append(p)
assert len(inputs)==len(set(inputs))==9
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='netstandard2.0',AssemblyName='System.Private.CoreLib.Generators',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='preview',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd',Version='10.0.5',AssemblyVersion='10.0.0.0',FileVersion=(root/'file-version.txt').read_text().strip(),InformationalVersion='10.0.5+081d220c0a773ffb7c6bea6b48727833576a65ef',IncludeSourceRevisionInInformationalVersion='false').items():E.SubElement(pg,k).text=v
items=E.SubElement(p,'ItemGroup')
for file in inputs:E.SubElement(items,'Compile',Include=native(file))
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.14.0]')
cap=E.SubElement(p,'Target',Name='CaptureActualCompilerInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(cap,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.indent(p);E.ElementTree(p).write(folder/'Build.csproj',encoding='utf-8',xml_declaration=True)
(folder/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(folder/'source-inputs.json').write_text(json.dumps(dict(original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),original_cs={p.relative_to(source).as_posix():sha(p) for p in inputs},original_framework='netstandard2.0',original_roslyn_version=version,production_source_changes=0),indent=2)+'\n')
print('PASS original nine-source Standard2.0 CoreLib event/product generators and Roslyn4.14 dependency')
