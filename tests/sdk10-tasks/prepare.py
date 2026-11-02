"""Evaluate original SDK10 task/APICompat source projects for their original source-only NET10 profile."""
from pathlib import Path
import hashlib,json,re,sys,tarfile,xml.etree.ElementTree as E
E.register_namespace('', 'http://schemas.microsoft.com/developer/msbuild/2003')
archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
assert sha(archive)=='3c9173ca31f070e662f705ebf6bc58c5a809fba78a407c3fb1f14274582ec85d'
with tarfile.open(archive) as t:t.extractall(out/'source',filter='data')
source=next((out/'source').iterdir()).resolve();removed=[]
for p in source.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.obj','.lib','.nupkg','.resources','.winmd'}:removed.append(dict(path=p.relative_to(source).as_posix(),sha256=sha(p)));p.unlink()
originals={};clones={};props=out/'props';props.mkdir()
for rel in ['Directory.Build.props','Directory.Build.targets','src/Compatibility/Directory.Build.props']:clones[rel]=props/rel.replace('/','-')
def clone(original,destination):
    tree=E.parse(original);tree.getroot().attrib.pop('Sdk',None)
    for parent in tree.iter():
        for item in list(parent):
            if item.tag.rsplit('}',1)[-1]=='Import' and item.get('Sdk'):parent.remove(item)
    for item in tree.iter():
        tag=item.tag.rsplit('}',1)[-1]
        for attr,value in list(item.attrib.items()):
            value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
            if tag=='Import' and attr=='Project' and not any(x in value for x in ['$(','@(','%(']):
                target=(original.parent/value).resolve();rel=target.relative_to(source).as_posix() if target.is_relative_to(source) else None;value=native(clones[rel]) if rel in clones else native(target)
            if tag in {'Compile','EmbeddedResource','ProjectReference','None','Content'} and attr in {'Include','Exclude','Remove','Update'}:
                parts=[]
                for part in value.split(';'):
                    if part and not any(x in part for x in ['$(','@(','%(']) and not Path(part).is_absolute():part=native(original.parent/part)
                    parts.append(part)
                value=';'.join(parts)
            item.set(attr,value)
        if item.text:item.text=item.text.replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
    tree.write(destination,encoding='utf-8',xml_declaration=True);originals[original.relative_to(source).as_posix()]=sha(original)
for rel,path in clones.items():clone(source/rel,path)
projects={
'Microsoft.DotNet.ApiSymbolExtensions':'src/Compatibility/Microsoft.DotNet.ApiSymbolExtensions/Microsoft.DotNet.ApiSymbolExtensions.csproj',
'Microsoft.DotNet.ApiCompatibility':'src/Compatibility/ApiCompat/Microsoft.DotNet.ApiCompatibility/Microsoft.DotNet.ApiCompatibility.csproj',
'Microsoft.DotNet.PackageValidation':'src/Compatibility/ApiCompat/Microsoft.DotNet.PackageValidation/Microsoft.DotNet.PackageValidation.csproj',
'Microsoft.DotNet.ApiCompat.Task':'src/Compatibility/ApiCompat/Microsoft.DotNet.ApiCompat.Task/Microsoft.DotNet.ApiCompat.Task.csproj',
'Microsoft.NET.Build.Extensions.Tasks':'src/Tasks/Microsoft.NET.Build.Extensions.Tasks/Microsoft.NET.Build.Extensions.Tasks.csproj',
'Microsoft.NET.Build.Tasks':'src/Tasks/Microsoft.NET.Build.Tasks/Microsoft.NET.Build.Tasks.csproj'}
wrappers={}
for name,rel in projects.items():
    original=source/rel;folder=out/name;folder.mkdir();clone(original,folder/'upstream.proj');root=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(root,'PropertyGroup')
    values=dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',NetCurrent='net10.0',NetToolMinimum='net10.0',NetFrameworkToolCurrent='net472',DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',DotNetBuild='true',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableDefaultCompileItems='false',EnableDefaultEmbeddedResourceItems='false',RepoRoot=native(source)+'/',RepositoryEngineeringDir=native(source/'eng')+'/',ArtifactsDir=native(out/'artifacts')+'/',ArtifactsBinDir=native(out/'artifacts/bin')+'/',ArtifactsTmpDir=native(out/'artifacts/tmp')+'/',AssemblyName=name,RootNamespace=name,DefineConstants='TRACE;NET;NETCOREAPP;NET10_0',MicrosoftNETCoreAppRefPackageVersion='10.0.5',MicrosoftNETCoreAppRuntimePackageVersion='10.0.5',MicrosoftAspNetCoreAppRefPackageVersion='10.0.5',MicrosoftAspNetCoreAppRuntimePackageVersion='10.0.5',PortableTargetRid='win-x64',TargetRid='win-x64',StrongNameKeyId='MicrosoftShared',IsTestProject='false',Nullable='enable',EnableNETAnalyzers='false',NuGetAudit='false')
    for k,v in values.items():E.SubElement(pg,k).text=v
    E.SubElement(root,'Import',Project=native(source/'eng/Versions.props'));E.SubElement(root,'Import',Project=native(clones['src/Compatibility/Directory.Build.props' if rel.startswith('src/Compatibility/') else 'Directory.Build.props']))
    disabled=any(p.text=='false' for p in E.parse(original).iter('EnableDefaultCompileItems')) or any(p.text=='false' for p in E.parse(original).iter('EnableDefaultItems'))
    if not disabled:
        ig=E.SubElement(root,'ItemGroup');exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**'
        if name=='Microsoft.DotNet.ApiSymbolExtensions':exclude+=';'+native(original.parent/'Logging/MSBuildLog.cs')
        E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=exclude);E.SubElement(ig,'EmbeddedResource',Include=native(original.parent)+'/**/*.resx')
    E.SubElement(root,'Import',Project=native(folder/'upstream.proj'));E.SubElement(root,'Import',Project=native(clones['Directory.Build.targets']))
    p=folder/(name+'.csproj');E.ElementTree(root).write(p,encoding='utf-8',xml_declaration=True);wrappers[name]=native(p)
# Rebind shared projitems' MSBuildThisFileDirectory while preserving all item metadata.
shared=source/'src/Compatibility/ApiCompat/Microsoft.DotNet.ApiCompat.Shared/Microsoft.DotNet.ApiCompat.Shared.projitems';target=props/'ApiCompat.Shared.projitems';clone(shared,target)
p=out/'Microsoft.DotNet.ApiCompat.Task/upstream.proj';tree=E.parse(p)
for e in tree.getroot().findall('Import'):
    if 'Microsoft.DotNet.ApiCompat.Shared.projitems' in e.get('Project',''):e.set('Project',native(target))
tree.write(p,encoding='utf-8',xml_declaration=True)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n');(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),archive_sha256=sha(archive),original_project_policy_sha256=originals,original_projects=projects,removed_binary_inputs=removed,original_production_source_changes=0,original_profile='DotNetBuildSourceOnly=true;net10.0',full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS prepared six original SDK10 NET10 project wrappers; project edges and metadata preserved')
