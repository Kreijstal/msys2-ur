"""Prepare unchanged NuGet6.13.2 source projects for their original VMR NET10 profile."""
from pathlib import Path
import hashlib,json,re,sys,tarfile,xml.etree.ElementTree as E

archive,out=(Path(p).resolve() for p in sys.argv[1:3]);closure=sys.argv[3:]==['--closure'];assert not sys.argv[3:] or closure;out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
assert sha(archive)=='3af9c4cd626db52aa51e63da9bd7e80f6944011ebf0a91a5c2b51f08dda731f1'
with tarfile.open(archive) as t:t.extractall(out/'source',members=[m for m in t.getmembers() if len(Path(m.name).parts)<2 or Path(m.name).parts[1] not in ['test','docs','.github']],filter='data')
source=next((out/'source').iterdir()).resolve();removed=[]
for p in source.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.lib','.obj','.resources'}:removed.append(dict(path=p.relative_to(source).as_posix(),sha256=sha(p)));p.unlink()
wrappers={};originals={}
names=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.Configuration','NuGet.Packaging','NuGet.Protocol','NuGet.Credentials']
for name in names:
    original=source/'src/NuGet.Core'/name/(name+'.csproj');folder=out/name;folder.mkdir()
    tree=E.parse(original);tree.getroot().attrib.pop('Sdk',None)
    for item in tree.iter():
        for attr,value in list(item.attrib.items()):
            value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
            if item.tag in {'Compile','ProjectReference','EmbeddedResource','Import'} and attr in {'Include','Update','Remove','Project'} and not any(t in value for t in ['$(', '@(', '%(']) and not Path(value).is_absolute():value=native(original.parent/value)
            item.set(attr,value)
    tree.write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True);originals[original.relative_to(source).as_posix()]=sha(original)
    p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
    for k,v in dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',DotNetBuildSourceOnly='true',DotNetBuild='true',BuildNumber='1',BuildRTM='true',BUILD_SOURCEVERSION='5d81cb8da82eda8a6b47aae92d1e6f888de982ce',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',AssemblyName=name,RootNamespace=name,SignWithMicrosoftKey='true').items():E.SubElement(pg,k).text=v
    E.SubElement(p,'Import',Project=native(source/'build/common.props'))
    pg=E.SubElement(p,'PropertyGroup');E.SubElement(pg,'DefineConstants').text='$(DefineConstants);NET;NETCOREAPP;NET10_0'
    ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**');E.SubElement(ig,'EmbeddedResource',Include=native(original.parent)+'/**/*.resx')
    E.SubElement(p,'Import',Project=native(folder/'upstream.proj'));E.SubElement(p,'Import',Project=native(source/'build/common.targets'));E.SubElement(p,'Import',Project=native(source/'Directory.Packages.props'))
    project=folder/(name+'.csproj');E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True);wrappers[name]=native(project)
for rel in ['build/config.props','build/common.props','build/common.project.props','build/common.targets','build/sign.targets']:originals[rel]=sha(source/rel)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_archive_sha256=sha(archive),original_project_inputs_sha256=originals,removed_binary_fixtures=removed,requested_original_profile='DotNetBuildSourceOnly=true;net10.0',original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(names),'original NuGet6.13.2 VMR NET10 project wrappers prepared;original production source unchanged')
