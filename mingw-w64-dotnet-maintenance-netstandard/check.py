"""Restore exact source-only netstandard2.0 packages and run isolated implementations."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

resume='--resume' in sys.argv[1:]
args=[p for p in sys.argv[1:] if p!='--resume']
root,out,consumer=(Path(p).resolve() for p in args[:3])
installed=len(args)==4
selected_feed=Path(args[3]).resolve() if installed else out/'feed'
assert resume or not consumer.exists(),consumer
consumer.mkdir(parents=True,exist_ok=resume)
here=Path(__file__).resolve().parent
manifest=json.loads((out/'source-inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(consumer/'cli-home'),NUGET_PACKAGES=native(consumer/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command,log):
    with log.open('w') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,(command,log)
config=E.Element('configuration');feeds=E.SubElement(config,'packageSources');E.SubElement(feeds,'clear')
feed_paths=[selected_feed,Path('/clang64/lib/dotnet/library-packs')]
for i,path in enumerate(feed_paths):E.SubElement(feeds,'add',key='source'+str(i),value=native(path))
E.ElementTree(config).write(consumer/'NuGet.config',encoding='utf-8',xml_declaration=True)
def project(path,properties,files,packages):
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    for k,v in dict(EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseAppHost='false',UseSharedCompilation='false',AllowUnsafeBlocks='true',LangVersion='preview',**properties).items():E.SubElement(pg,k).text=v
    ig=E.SubElement(tree,'ItemGroup')
    for file in files:E.SubElement(ig,'Compile',Include=native(file))
    for name,version in packages.items():E.SubElement(ig,'PackageReference',Include=name,Version='['+version+']')
    E.indent(tree);E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
library=consumer/'library';library.mkdir(exist_ok=resume)
versions={n:r['version'] for n,r in manifest['projects'].items()}
project(library/'Build.csproj',dict(TargetFramework='netstandard2.0',AssemblyName='MaintenanceConsumer',CopyLocalLockFileAssemblies='true'),[here/'inputs/Consumer.cs'],versions)
def build(proj,log):run([dotnet,'build',native(proj),'-c','Release','--configfile',native(consumer/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],log)
build(library/'Build.csproj',consumer/'library-build.log')
target=library/'bin/Release/netstandard2.0'
for name,version in versions.items():assert (target/(name+'.dll')).is_file(),name
runner=consumer/'runner';runner.mkdir(exist_ok=resume)
project(runner/'Build.csproj',dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='CheckMaintenance',Nullable='enable'),[here/'inputs/Check.cs'],{'Microsoft.CodeAnalysis.CSharp':'4.9.2'})
build(runner/'Build.csproj',consumer/'runner-build.log')
run([dotnet,native(runner/'bin/Release/net8.0/CheckMaintenance.dll'),native(out),native(target),native(consumer/'runtime-results.json'),native(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0'))],consumer/'run.log')
runtime=json.loads((consumer/'runtime-results.json').read_text())
feed_files={}
for feed in feed_paths:
    for file in feed.glob('*.nupkg'):feed_files.setdefault(file.name.lower(),file)
package_audits=[]
for assets_file in [library/'obj/project.assets.json',runner/'obj/project.assets.json',*[out/n/'obj/project.assets.json' for n in manifest['order'][1:]]]:
    assets=json.loads(assets_file.read_text());folders=list(assets['packageFolders']);assert len(folders)==1
    native_folder=folders[0].replace('\\','/').rstrip('/')
    assert native_folder.lower().startswith(native_root.lower()+'/'),native_folder
    cache=root/native_folder[len(native_root)+1:]
    for name,record in assets['libraries'].items():
        if record['type']!='package':continue
        ident,version=name.split('/');filename=ident.lower()+'.'+version+'.nupkg';assert filename in feed_files,name
        actual=cache/record['path']/filename;expected=feed_files[filename]
        assert sha(actual)==sha(expected),(name,assets_file)
        with zipfile.ZipFile(expected) as z:
            for path in z.namelist():
                if path.endswith('.dll'):assert (cache/record['path']/path).read_bytes()==z.read(path),(name,path)
        package_audits.append(dict(consumer=native(assets_file),package=name,sha256=sha(expected)))
assets=json.loads((library/'obj/project.assets.json').read_text())
assert set(assets['libraries'])==set(n+'/'+v for n,v in versions.items())|{'NETStandard.Library/2.0.3','Microsoft.NETCore.Platforms/1.1.2'}
for name,version in versions.items():
    with zipfile.ZipFile(out/'feed'/(name+'.'+version+'.nupkg')) as z:
        assert (target/(name+'.dll')).read_bytes()==z.read('lib/netstandard2.0/'+name+'.dll'),name
        assert z.read('LICENSE'),name
selected={c:{} for c in manifest['archives']}
for name,r in manifest['projects'].items():
    wanted=selected[r['commit']];wanted[r['original_project']]=r['original_project_sha256']
    wanted.update(r['original_sources']);wanted.update(r['original_extra_inputs'])
source_audits={}
for commit,(filename,digest) in manifest['archives'].items():
    archive=root/filename;assert sha(archive)==digest;verified=set()
    with tarfile.open(archive) as tar:
        assert tar.pax_headers['comment']==commit
        for member in tar:
            path=member.name.partition('/')[2]
            if member.isfile() and path in selected[commit]:
                assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==selected[commit][path],path
                assert sha(out/('maintenance-packages-'+commit)/path)==selected[commit][path],path
                verified.add(path)
    assert verified==set(selected[commit]);source_audits[commit]=dict(archive_sha256=digest,selected_original_inputs_verified=len(verified))
packages={}
for name,r in manifest['projects'].items():
    path=out/'feed'/(name+'.'+r['version']+'.nupkg')
    with zipfile.ZipFile(path) as z:
        spec=E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))))
        md=next(e for e in spec if e.tag.endswith('metadata'))
        values={e.tag.rsplit('}',1)[-1]:e.text for e in md}
        assert values['id']==name and values['version']==r['version']
        repository=next(e for e in md if e.tag.endswith('repository'));assert repository.get('commit')==r['commit']
        dependencies={e.get('id'):e.get('version').strip('[]') for e in md.iter() if e.tag.endswith('dependency')}
        assert dependencies==r['dependencies'],(name,dependencies)
        packages[name]=dict(version=r['version'],assembly_version=r['assembly_version'],sha256=sha(path),dependencies=dependencies)
results=dict(source_archive_audits=source_audits,packages=packages,actual_source_compile_and_consumer_package_references_verified=len(package_audits),package_audits=package_audits,runtime=runtime,all_fresh_cache_and_production_compile_cache_dll_bytes_match_source=True,formal_pacman_installed=installed,complete_shipping_generator_bundle_built=False,full_dependency_goal_complete=False)
(consumer/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS five exact-source netstandard2.0 packages, isolated runtime/API/resource checks, pinned archives and actual compiler/consumer dependency bytes')
