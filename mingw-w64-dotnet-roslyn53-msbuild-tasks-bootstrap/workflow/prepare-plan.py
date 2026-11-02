"""Extract pinned MSBuild source and clone original NET10 evaluation projects."""
from pathlib import Path
import hashlib,json,os,re,sys,tarfile,xml.etree.ElementTree as E
archive,out=(Path(p).resolve() for p in sys.argv[1:3]);legacy=sys.argv[3:]==['--msbuild-17.11-net8'];assert not sys.argv[3:] or legacy
assert not out.exists();out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='d862cc76d748f649894ec189fb6f6e9dabec8dbd2e96505650b0a487ba645d53' if legacy else 'fff679ff42b8f821d75c31921ad938900bf66c530a143ddef27c5ce239736e45'
assert sha(archive)==expected
with tarfile.open(archive) as tar:tar.extractall(out/'source',filter='data')
source=next((out/'source').iterdir()).resolve();removed=[]
for p in source.rglob('*'):
 if p.is_file() and (p.suffix.lower() in {'.dll','.exe','.pdb','.lib','.obj','.nupkg','.resources'}):
  removed.append(dict(path=p.relative_to(source).as_posix(),sha256=sha(p)));p.unlink()
native=lambda p:Path(p).as_posix()
props=out/'props';props.mkdir();originals={};clones={}
names=['Directory.Build.props','src/Directory.Build.props','Directory.Build.targets','src/Directory.Build.targets']
for i,name in enumerate(names):clones[name]=props/(str(i)+'-'+Path(name).name)
def clone(original,destination):
 tree=E.parse(original);root=tree.getroot();root.attrib.pop('Sdk',None)
 for parent in root.iter():
  for item in list(parent):
   if item.tag=='Import' and item.get('Sdk')=='Microsoft.DotNet.Arcade.Sdk':parent.remove(item)
 for item in root.iter():
  for attr in list(item.attrib):
   value=item.get(attr).replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
   if attr=='Project' and item.tag=='Import' and not any(x in value for x in ['$(','@(','%(']):
    target=(original.parent/value).resolve() if not Path(value).is_absolute() else Path(value)
    if target.is_relative_to(source) and target.relative_to(source).as_posix() in clones:value=native(clones[target.relative_to(source).as_posix()])
    else:value=native(target)
   elif item.tag in {'Compile','ProjectReference','EmbeddedResource','AdditionalFiles','None','Content','RCResourceFile','EditorConfigFiles'} and attr in {'Include','Remove','Update','Exclude'}:
    pieces=[]
    for part in value.split(';'):
     if part and not any(x in part for x in ['$(','@(','%(']) and not Path(part).is_absolute() and not re.match(r'^[a-zA-Z]:/',part):part=native(original.parent/part)
     pieces.append(part)
    value=';'.join(pieces)
   item.set(attr,value)
 for item in root.iter():
  if item.text:item.text=item.text.replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
 E.indent(tree);tree.write(destination,encoding='utf-8',xml_declaration=True);originals[original.relative_to(source).as_posix()]=sha(original)
for name in names:clone(source/name,clones[name])
projects={
 'Microsoft.NET.StringTools':'src/StringTools/StringTools.csproj',
 'Microsoft.Build.Framework':'src/Framework/Microsoft.Build.Framework.csproj',
 'Microsoft.Build':'src/Build/Microsoft.Build.csproj',
 'Microsoft.Build.Utilities.Core':'src/Utilities/Microsoft.Build.Utilities.csproj',
 'Microsoft.Build.Tasks.Core':'src/Tasks/Microsoft.Build.Tasks.csproj',
 'MSBuild':'src/MSBuild/MSBuild.csproj',
}
wrappers={}
for name,relative in projects.items():
 original=source/relative;folder=out/'projects'/name;folder.mkdir(parents=True);clone(original,folder/'upstream.proj')
 root=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(root,'PropertyGroup')
 values=dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',NetCurrent='net10.0',NetPrevious='net9.0',DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',DotNetBuild='true',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultCompileItems='false',EnableDefaultEmbeddedResourceItems='false',EnableDefaultNoneItems='false',RepoRoot=native(source)+'/',RepositoryEngineeringDir=native(source/'eng')+'/',ArtifactsDir=native(out/'artifacts')+'/',AssemblyName=name,DefineConstants='TRACE;RELEASE;NET;NETCOREAPP;NET10_0',IsTestProject='false',IsUnitTestProject='false',CustomBeforeMicrosoftCommonTargets=native(source/'src/Directory.BeforeCommon.targets'))
 if legacy:values.update(TargetFramework='net8.0',TargetFrameworkVersion='v8.0',NetCurrent='net8.0',NetPrevious='net7.0',DefineConstants='TRACE;RELEASE;NET;NETCOREAPP;NET8_0',DotNetBuildFromSource='true')
 for k,v in values.items():E.SubElement(pg,k).text=v
 E.SubElement(root,'Import',Project=native(source/'eng/Versions.props'))
 E.SubElement(root,'Import',Project=native(clones['src/Directory.Build.props']))
 explicit_disabled=any(e.text=='false' for e in E.parse(original).iter('EnableDefaultItems'))
 if not explicit_disabled:
  items=E.SubElement(root,'ItemGroup')
  E.SubElement(items,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**')
  E.SubElement(items,'EmbeddedResource',Include=native(original.parent)+'/**/*.resx')
 E.SubElement(root,'Import',Project='upstream.proj')
 E.SubElement(root,'Import',Project=native(clones['src/Directory.Build.targets']))
 E.indent(root);p=folder/original.name;E.ElementTree(root).write(p,encoding='utf-8',xml_declaration=True);wrappers[name]=native(p)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_archive_sha256=sha(archive),original_inputs_sha256=originals,removed_binary_inputs=removed,original_production_source_changes=0,requested_original_profile=('net8.0;DotNetBuildFromSource=true' if legacy else 'net10.0;DotNetBuildSourceOnly=true;DotNetBuildFromVMR=true'),compiled=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('Prepared six original MSBuild projects; removed',len(removed),'binary inputs')
