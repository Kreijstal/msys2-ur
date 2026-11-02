"""Restore the three packaged roots with original central transitive pinning and WAE."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

candidate,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';tools=prefix/'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin'
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
doc=candidate/'share/doc/dotnet-templateengine10-bootstrap';models=json.loads((doc/'evaluated-projects.json').read_text());archives=json.loads((doc/'archives.json').read_text())
view=out/'source-feed';view.mkdir();selected={}
for base in [candidate/'lib/dotnet/library-packs',prefix/'lib/dotnet/library-packs']:
    for archive in base.glob('*.nupkg'):selected.setdefault(archive.name.lower(),archive)
for name,archive in selected.items():
    target=view/name
    try:os.link(archive,target)
    except OSError:shutil.copyfile(archive,target)
    assert sha(archive)==sha(target)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="exact-source-view" value="'+native(view)+'"/></packageSources></configuration>')
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',ManagePackageVersionsCentrally='true',CentralPackageVersionsFileImported='true',CentralPackageTransitivePinningEnabled='true',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(out/'obj')+'/',BaseIntermediateOutputPath=native(out/'obj')+'/',RestoreConfigFile=native(out/'NuGet.config'),RestorePackagesPath=native(out/'cache'),RestoreTaskAssemblyFile=native(tools/'NuGet.Build.Tasks.dll'),NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,k).text=v
central={}
for model in models.values():
    for item in model['items']['PackageVersion']:
        version=item['metadata'].get('Version')
        if version:
            assert item['identity'] not in central or central[item['identity']]==version
            central[item['identity']]=version
ig=E.SubElement(p,'ItemGroup')
for name,version in central.items():E.SubElement(ig,'PackageVersion',Include=name,Version=version)
roots=['Microsoft.TemplateEngine.Edge','Microsoft.TemplateEngine.Orchestrator.RunnableProjects','Microsoft.TemplateSearch.Common']
for name in roots:
    E.SubElement(ig,'PackageVersion',Include=name,Version='[10.0.200-preview.26113.113]')
    E.SubElement(ig,'PackageReference',Include=name)
E.SubElement(p,'Import',Project=native(tools/'NuGet.targets'));E.ElementTree(p).write(out/'Restore.proj',encoding='utf-8',xml_declaration=True)
cmd=[host,tools/'MSBuild.dll',out/'Restore.proj','-t:Restore','-nologo','-v:minimal']
with (out/'restore.log').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache')),timeout=180)
assert r.returncode==0,r.returncode
assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets.get('logs'),assets.get('logs')
actual={}
for identity in assets['libraries']:
    name,version=identity.split('/');cached=out/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg');original=selected[cached.name]
    assert cached.read_bytes()==original.read_bytes()
    actual[name]=dict(version=version,archive_SHA256=sha(cached))
for name in archives:
    assert actual[name]['version']=='10.0.200-preview.26113.113' and actual[name]['archive_SHA256']==archives[name]['sha256']
for name,version in {'NuGet.Configuration':'6.13.2','NuGet.Credentials':'6.13.2','NuGet.Protocol':'6.13.2','Microsoft.Extensions.Logging.Abstractions':'10.0.2','Newtonsoft.Json':'13.0.3','System.Formats.Asn1':'10.0.2'}.items():assert actual[name]['version']==version,(name,actual.get(name))
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd],exit_code=r.returncode,original_central_package_transitive_pinning_enabled=True,original_TreatWarningsAsErrors_applied=True,diagnostics=assets.get('logs',[]),selected_source_packages=actual,original_all_central_versions=central,actual_package_dependency_graph_restored=True,exact_cached_archive_bytes_verified=True,full_original_SDK_pruning_integration_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS three packaged TemplateEngine roots, seven exact archives, original CPM/WAE and unchanged support versions')
