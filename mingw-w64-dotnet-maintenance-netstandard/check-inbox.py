"""Verify original higher-framework placeholders select the source framework implementations."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

prepared,out=(Path(p).resolve() for p in sys.argv[1:3])
feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else prepared/'feed'
assert not out.exists();out.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
records=json.loads((prepared/'source-inputs.json').read_text())['projects']
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',AssemblyName='InboxProbe').items():E.SubElement(pg,k).text=v
items=E.SubElement(tree,'ItemGroup')
for name,r in records.items():E.SubElement(items,'PackageReference',Include=name,Version='['+r['version']+']')
target=E.SubElement(tree,'Target',Name='CaptureReferences',BeforeTargets='CoreCompile')
E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)references.txt',Lines="@(ReferencePath->'%(FullPath)')",Overwrite='true')
E.indent(tree);E.ElementTree(tree).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'Program.cs').write_text('''using System;
using System.Buffers;
using System.IO;
using System.Numerics;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
class Program {
 static int Main(string[] args) {
  string root=Path.GetFullPath(args[0])+Path.DirectorySeparatorChar;
  foreach(Type type in new[]{typeof(ArrayPool<byte>),typeof(Span<int>),typeof(Vector3),typeof(Unsafe),typeof(ValueTask)})
   if(!Path.GetFullPath(type.Assembly.Location).StartsWith(root,StringComparison.OrdinalIgnoreCase))throw new Exception("Unexpected inbox owner: "+type.Assembly.Location);
  if(Unsafe.SizeOf<long>()!=8 || new Vector3(1,2,3).LengthSquared()!=14)throw new Exception("Inbox execution failed");
  Console.WriteLine("PASS original higher-framework placeholders select source framework implementations");
  return 0;
 }
}
''')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(feed)+'"/></packageSources></configuration>')
env=dict(os.environ,DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
with (out/'build.log').open('w') as log:
 subprocess.run([dotnet,'build',native(out/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assets=json.loads((out/'obj/project.assets.json').read_text());assert set(assets['libraries'])=={n+'/'+r['version'] for n,r in records.items()}
selected=next(iter(assets['targets'].values()));paths={}
for name,r in records.items():
 item=selected[name+'/'+r['version']];paths[name]={kind:list(item.get(kind,{})) for kind in ['compile','runtime']}
 assert not any(p.lower().endswith('.dll') for kind in paths[name].values() for p in kind),(name,paths[name])
 assert not (out/'bin/Release/net8.0'/(name+'.dll')).exists(),name
references=(out/'obj/Release/net8.0/references.txt').read_text(encoding='utf-8-sig').splitlines()
prefix=native(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')).lower()+'/'
for name in records:
 found=[p.replace('\\','/') for p in references if p.replace('\\','/').rsplit('/',1)[-1]==name+'.dll']
 assert len(found)==1 and found[0].lower().startswith(prefix),(name,found)
with (out/'run.log').open('w') as log:
 subprocess.run([dotnet,native(out/'bin/Release/net8.0/InboxProbe.dll'),native(Path('/clang64/lib/dotnet/shared/Microsoft.NETCore.App/8.0.31'))],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'results.json').write_text(json.dumps(dict(selected_package_assets=paths,all_five_framework_reference_paths_verified=True,all_five_runtime_type_owners_in_source_framework=True,no_portable_implementation_dll_copied=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS all five original inbox selections, actual framework references and source-framework execution')
