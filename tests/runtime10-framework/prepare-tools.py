"""Build original resource-source and complete ILLink task sources for the NET8 host."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
source=root/'r';arcade=root/'arcade-runtime10-4bf37ce6.tar.gz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(arcade)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
folder=out/'tools';folder.mkdir();inputs={}
with tarfile.open(arcade) as t:
 assert t.pax_headers['comment']=='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d'
 for m in t:
  if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/src/GenerateResxSource.cs'):
   file=folder/'GenerateResxSource.cs';file.write_bytes(t.extractfile(m).read());inputs['Arcade.GenerateResxSource']=dict(source_commit=t.pax_headers['comment'],original_cs_sha256=sha(file))
  if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/tools/StrongName.props'):
   (folder/'StrongName.props').write_bytes(t.extractfile(m).read())
  if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/tools/GenerateResxSource.targets'):
   (folder/'GenerateResxSource.targets').write_bytes(t.extractfile(m).read())
projects={}
for name,cs in [('Framework10.Arcade.Resources',[folder/'GenerateResxSource.cs']),('ILLink.Tasks',sorted((source/'src/tools/illink/src/ILLink.Tasks').glob('*.cs')))]:
 target=folder/name;target.mkdir();assert len(cs)==(1 if name.startswith('Framework10') else 5)
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',AssemblyName=name,EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',LangVersion='preview',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
 ig=E.SubElement(p,'ItemGroup')
 for file in cs:E.SubElement(ig,'Compile',Include=native(file))
 for assembly in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.Build.Tasks.Core']:
  r=E.SubElement(ig,'Reference',Include=assembly);E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/sdk/8.0.131')/(assembly+'.dll'));E.SubElement(r,'Private').text='false'
 if name=='ILLink.Tasks':
  for assembly in ['Mono.Cecil','illink']:
   r=E.SubElement(ig,'Reference',Include=assembly);E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap')/(assembly+'.dll'));E.SubElement(r,'Private').text='false'
 E.indent(p);E.ElementTree(p).write(target/'Build.csproj',encoding='utf-8',xml_declaration=True);projects[name]=native(target/'Build.csproj')
 inputs[name]=dict(original_sources={str(p):sha(p) for p in cs},production_cs_changes=0,bootstrap_framework='net8.0',original_net10_host_verified=False)
(folder/'projects.json').write_text(json.dumps(projects,indent=2)+'\n');(folder/'source-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
print('PASS original Arcade resource generator and all five ILLink task sources prepared')
