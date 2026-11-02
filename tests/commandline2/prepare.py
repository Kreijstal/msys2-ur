"""Preserve exact SDK10 VMR CommandLine2 source and its original NET10/NS2 project profiles."""
from pathlib import Path
import hashlib,json,sys,tarfile,xml.etree.ElementTree as E
archive,arcade_archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
assert sha(archive)=='ee5149b6dc17074dd8dbc1c61b1a2e6ae22f3491a8f0019f72ec286672645cb1';assert sha(arcade_archive)=='5df0a134ed5218656135316ba1a3aed7cfa261241fa0be0bef7560e1c4b0bb83'
with tarfile.open(archive) as t:t.extractall(out/'snapshot',filter='data')
source=out/'snapshot/command-line-api';origin=json.loads((out/'snapshot/vmr-source-inputs.json').read_text())
for rel,v in origin['files'].items():assert sha(source/rel)==v['sha256'],rel
arcade=out/'arcade';arcade.mkdir();wanted=['tools/ProjectDefaults.props','tools/TargetFrameworkDefaults.props','tools/Version.BeforeCommonTargets.targets','tools/Version.targets','src/CalculateAssemblyAndFileVersions.cs','tools/GenerateResxSource.targets']
with tarfile.open(arcade_archive) as t:
 for m in t:
  if not m.isfile():continue
  suffix=next((rel for rel in wanted if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/'+rel)),None)
  if suffix:(arcade/Path(suffix).name).write_bytes(t.extractfile(m).read())
assert len(list(arcade.iterdir()))==6
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(Configuration='Release',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName='System.CommandLine',RootNamespace='System.CommandLine',DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',DisableArcade='1',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
for file in [arcade/'ProjectDefaults.props',arcade/'TargetFrameworkDefaults.props',source/'eng/Versions.props',source/'Directory.Build.props']:E.SubElement(p,'Import',Project=native(file))
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(source/'src/System.CommandLine')+'/**/*.cs',Exclude=native(source/'src/System.CommandLine')+'/obj/**;'+native(source/'src/System.CommandLine')+'/bin/**');E.SubElement(ig,'EmbeddedResource',Include=native(source/'src/System.CommandLine/Properties/Resources.resx'))
original=source/'src/System.CommandLine/System.CommandLine.csproj';tree=E.parse(original);tree.getroot().attrib.pop('Sdk',None)
for item in tree.iter():
 for attr,value in list(item.attrib.items()):
  value=value.replace('\\','/')
  if item.tag in ['Compile','None','Import'] and attr in ['Include','Project'] and '$(' not in value and not Path(value).is_absolute():value=native(original.parent/value)
  item.set(attr,value)
tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True);E.SubElement(p,'Import',Project=native(out/'upstream.proj'));E.SubElement(p,'Import',Project=native(source/'Directory.Packages.props'));wrapper=out/'CommandLine.csproj';E.ElementTree(p).write(wrapper,encoding='utf-8',xml_declaration=True)
(out/'wrappers.json').write_text(json.dumps({tfm:native(wrapper) for tfm in ['net10.0','netstandard2.0']},indent=2)+'\n');(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_snapshot_sha256=sha(archive),arcade_archive_sha256=sha(arcade_archive),vmr_commit=origin['vmr_commit'],mapped_source_commit=origin['mapped_source_commit'],vmr_files_verified=len(origin['files']),vmr_version_policy_changes=origin['vmr_differences'],original_project_sha256=sha(original),original_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS405 exact VMR files;original CommandLine2 NET10 and NS2 profiles prepared')
