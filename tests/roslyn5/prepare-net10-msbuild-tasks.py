"""Evaluate original Roslyn SDK10 MSBuild task inputs without editing sources."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
native=lambda p:Path(p).resolve().as_posix()
task=source/'src/Compilers/Core/MSBuildTask';originals={}
def clone(original,destination,skip_parent=False):
    tree=E.parse(original);root=tree.getroot();root.attrib.pop('Sdk',None)
    for parent in root.iter():
        for item in list(parent):
            if skip_parent and item.tag=='Import' and 'GetPathOfFileAbove' in item.get('Project',''):parent.remove(item)
    for item in root.iter():
        for attr,value in list(item.attrib.items()):
            value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
            if item.tag in {'Import','Compile','EmbeddedResource','Content','None','ProjectReference'} and attr in {'Project','Include','Remove','Update'}:
                if not any(t in value for t in ['$(', '@(', '%(']) and not Path(value).is_absolute():value=native(original.parent/value)
            item.set(attr,value)
        if item.text:item.text=item.text.replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
    E.ElementTree(root).write(destination,encoding='utf-8',xml_declaration=True)
    originals[original.relative_to(source).as_posix()]=hashlib.sha256(original.read_bytes()).hexdigest()
clone(task/'Directory.Build.props',out/'Task.props',True)
clone(task/'Directory.Build.targets',out/'Task.targets',True)
clone(task/'MSBuild/Microsoft.Build.Tasks.CodeAnalysis.csproj',out/'upstream.proj')
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',NetCurrent='net10.0',NetPrevious='net9.0',NetMinimum='net8.0',DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableDefaultCompileItems='false',RepositoryEngineeringDir=native(source/'eng')+'/',RepoRoot=native(source)+'/',RootNamespace='Microsoft.CodeAnalysis.BuildTasks',AssemblyName='Microsoft.Build.Tasks.CodeAnalysis',DefineConstants='TRACE;RELEASE;NET;NETCOREAPP;NET10_0;DOTNET_BUILD_FROM_SOURCE').items():E.SubElement(pg,k).text=v
for rel in ['eng/Versions.props','eng/Packages.props','eng/targets/TargetFrameworks.props','eng/targets/Settings.props']:
    E.SubElement(p,'Import',Project=native(source/rel));originals[rel]=hashlib.sha256((source/rel).read_bytes()).hexdigest()
for rel in ['Task.props','upstream.proj','Task.targets']:E.SubElement(p,'Import',Project=native(out/rel))
project=out/'Microsoft.Build.Tasks.CodeAnalysis.csproj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
(out/'wrappers.json').write_text(json.dumps({'Microsoft.Build.Tasks.CodeAnalysis':native(project)},indent=2)+'\n')
(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),original_project_inputs_sha256=originals,original_source_changed=False,requested_framework='net10.0',full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NET10 Roslyn MSBuild task wrapper prepared')
