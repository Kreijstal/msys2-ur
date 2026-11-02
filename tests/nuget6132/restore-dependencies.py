"""Resolve unchanged NuGet6.13.2 NET10 package requirements against the installed source feed."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();native=lambda p:Path(p).resolve().as_posix();prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';tools=prefix/'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin';feed=prefix/'lib/dotnet/library-packs';models=json.loads((plan/'evaluated.json').read_text());requirements={}
for name,m in models.items():
 central={i['identity']:i['metadata']['Version'] for i in m['items']['PackageVersion'] if i['metadata'].get('Version')}
 for i in m['items']['PackageReference']:requirements[i['identity']]=central[i['identity']]
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(feed)+'"/></packageSources></configuration>');p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(out/'obj')+'/',BaseIntermediateOutputPath=native(out/'obj')+'/',RestoreConfigFile=native(out/'NuGet.config'),RestorePackagesPath=native(out/'cache'),RestoreTaskAssemblyFile=native(tools/'NuGet.Build.Tasks.dll'),NuGetAudit='false',TreatWarningsAsErrors='true').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for name,version in requirements.items():E.SubElement(ig,'PackageReference',Include=name,Version=version)
E.SubElement(p,'Import',Project=native(tools/'NuGet.targets'));E.ElementTree(p).write(out/'Dependencies.proj',encoding='utf-8',xml_declaration=True);cmd=[host,tools/'MSBuild.dll',out/'Dependencies.proj','-t:Restore','-nologo','-v:minimal']
with (out/'restore.log').open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache')),timeout=180)
assert r.returncode==0,r.returncode
assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets.get('logs'),assets.get('logs');packages={}
for identity,meta in assets['libraries'].items():
 name,version=identity.split('/');cached=out/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg');archive=next(p for p in feed.iterdir() if p.name.lower()==cached.name);assert cached.read_bytes()==archive.read_bytes();packages[name]=dict(version=version,archive=native(archive),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),compile_assets=assets['targets']['net10.0'][identity].get('compile',{}),runtime_assets=assets['targets']['net10.0'][identity].get('runtime',{}))
for package, version in {'System.Collections.Immutable':'8.0.0','System.Security.Cryptography.ProtectedData':'4.4.0','System.Security.Cryptography.Pkcs':'6.0.4','System.Formats.Asn1':'8.0.1','Newtonsoft.Json':'13.0.3'}.items():
 assert packages[package]['version']==version,(package,packages[package]['version'],version)
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd],exit_code=r.returncode,original_requirements=requirements,actual_source_packages=packages,source_archive_bytes_verified=True,restore_diagnostics=assets.get('logs',[]),original_requirements_changed=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS offline restore of original NuGet6.13.2 requirements:',{n:p['version'] for n,p in packages.items()})
