"""Prepare all original Core GenFacades task sources from runtime10's pinned Arcade."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
archive=root/'arcade-runtime10-4bf37ce6.tar.gz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
source=root/'arcade';source.mkdir();files={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d'
 for m in t:
  name=m.name.partition('/')[2]
  if m.isfile() and (name.startswith('src/Microsoft.DotNet.GenFacades/') or name in ['src/Common/Internal/BuildTask.cs','eng/Version.Details.props','src/Microsoft.DotNet.Arcade.Sdk/tools/TargetFrameworkDefaults.props','LICENSE.TXT']):
   p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read());files[name]=sha(p)
project=source/'src/Microsoft.DotNet.GenFacades/Microsoft.DotNet.GenFacades.csproj'
assert E.parse(project).findtext('.//TargetFrameworks')=='$(NetToolCurrent);$(NetFrameworkToolCurrent)'
inputs=sorted(project.parent.glob('*.cs'))+[source/'src/Common/Internal/BuildTask.cs'];assert len(inputs)==8
out=root/'build';out.mkdir()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='Microsoft.DotNet.GenFacades',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',LangVersion='preview',Version='10.0.5',AssemblyVersion='10.0.0.0',FileVersion='10.0.526.11800',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd',GenerateDependencyFile='true',CopyLocalLockFileAssemblies='true').items():E.SubElement(pg,k).text=v
items=E.SubElement(p,'ItemGroup')
for file in inputs:E.SubElement(items,'Compile',Include=native(file))
for name in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.Build.Tasks.Core']:
 r=E.SubElement(items,'Reference',Include=name);E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/sdk/8.0.131')/(name+'.dll'));E.SubElement(r,'Private').text='false'
E.SubElement(items,'PackageReference',Include='Microsoft.CodeAnalysis.CSharp',Version='[4.14.0]')
t=E.SubElement(p,'Target',Name='CaptureInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(t,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
E.indent(p);E.ElementTree(p).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
(root/'source-inputs.json').write_text(json.dumps(dict(arcade_commit='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d',arcade_archive_sha256=sha(archive),archive_files=files,original_cs={p.relative_to(source).as_posix():sha(p) for p in inputs},production_cs_changes=0,original_frameworks=['net10.0','net472'],bootstrap_framework='net8.0',declared_roslyn_version='4.8.0',bootstrap_roslyn_version='4.14.0',declared_msbuild_tasks_version='17.12.50',bootstrap_msbuild_version='17.8.49',full_original_tool_profiles_complete=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS eight unchanged original GenFacades sources and four original target files')
