"""Evaluate original TemplateEngine NET10 source-only projects with verified VMR version flow."""
from pathlib import Path
import hashlib,json,sys,tarfile,xml.etree.ElementTree as E
archive,flow,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(archive)=='e78c80f2a710a26157d7cc95ee62e1dae48cbaa40c3a70d7472c29b461f4cbbb';checked=json.loads((flow/'results.json').read_text());assert checked['logging_Runtime1002_and_CommandLine202_flow_verified'] and checked['original_NuGet6132_requirements_preserved']
with tarfile.open(archive) as t:t.extractall(out/'snapshot',filter='data')
source=out/'snapshot/templating';manifest=json.loads((out/'snapshot/source-inputs.json').read_text());assert len(manifest['files'])==1891
for rel,h in manifest['files'].items():assert sha(source/rel)==h['sha256'],rel
names=['Microsoft.TemplateEngine.Abstractions','Microsoft.TemplateEngine.Core.Contracts','Microsoft.TemplateEngine.Utils','Microsoft.TemplateEngine.Core','Microsoft.TemplateEngine.Orchestrator.RunnableProjects','Microsoft.TemplateEngine.Edge','Microsoft.TemplateSearch.Common'];wrappers={};originals={}
def clone(path,dest):
 tree=E.parse(path);root=tree.getroot();root.attrib.pop('Sdk',None)
 for imp in list(root.findall('Import')):
  if imp.get('Sdk')=='Microsoft.DotNet.Arcade.Sdk':root.remove(imp)
 for item in tree.iter():
  for attr,value in list(item.attrib.items()):
   value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(path.parent)+'/')
   if item.tag in ['Compile','EmbeddedResource','ProjectReference'] and attr in ['Include','Update','Remove','Exclude']:
    value=';'.join(native(path.parent/v) if v and not any(s in v for s in ['$(', '@(', '%(']) and not Path(v).is_absolute() else v for v in value.split(';'))
   item.set(attr,value)
 tree.write(dest,encoding='utf-8',xml_declaration=True)
clone(source/'Directory.Build.props',out/'upstream.props');clone(source/'Directory.Build.targets',out/'upstream.targets')
for name in names:
 folder=out/name;folder.mkdir();original=source/'src'/name/(name+'.csproj');clone(original,folder/'upstream.proj');originals[original.relative_to(source).as_posix()]=sha(original)
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 for k,v in dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',NetCurrent='net10.0',NetToolCurrent='net10.0',DotNetBuildSourceOnly='true',RepoRoot=native(source)+'/',SrcDir=native(source/'src')+'/',RootNamespace=name,AssemblyName=name,EnableDefaultItems='false',EnableDefaultCompileItems='false',EnableDefaultEmbeddedResourceItems='false',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',VersionsPropsPath=native(source/'eng/Versions.props'),DotNetPackageVersionPropsPath=native(flow/'versions.props'),NuGetAudit='false').items():E.SubElement(pg,k).text=v
 E.SubElement(p,'Import',Project=native(flow/'arcade/DefaultVersions.props'));E.SubElement(p,'Import',Project=native(out/'upstream.props'))
 ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**');E.SubElement(ig,'EmbeddedResource',Include=native(original.parent)+'/**/*.resx')
 E.SubElement(p,'Import',Project=native(folder/'upstream.proj'));E.SubElement(p,'Import',Project=native(out/'upstream.targets'));E.SubElement(p,'Import',Project=native(source/'Directory.Packages.props'))
 wrapper=folder/(name+'.csproj');E.ElementTree(p).write(wrapper,encoding='utf-8',xml_declaration=True);wrappers[name]=dict(path=native(wrapper),framework='net10.0')
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n');(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_archive_sha256=sha(archive),VMR_manifest=manifest,original_projects_sha256=originals,verified_original_version_flow=checked,original_production_source_changes=0,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS seven original TemplateEngine NET10 project wrappers with original VMR/Arcade version flow')
