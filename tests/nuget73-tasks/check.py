"""Execute original pack/restore/static-graph tasks and SDK resolution with offline Unicode consumers."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E,zipfile
plan,build,out=(Path(p).resolve() for p in sys.argv[1:4]);installed_runtime=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None;out.mkdir();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';original_msbuild=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();commands=[]
stage=out/'runtime'
if installed_runtime is not None:shutil.copytree(installed_runtime,stage)
else:
 shutil.copytree(original_msbuild,stage)
 for folder in [build/'bin',build/'dependency-assets']:
  for p in folder.glob('*'):
   if p.is_file():shutil.copyfile(p,stage/p.name)
 feed=prefix/'lib/dotnet/library-packs'
 for name,version,member in [('System.Security.Cryptography.Pkcs','8.0.1','runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'),('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll'),('Microsoft.Extensions.FileSystemGlobbing','6.0.0','lib/net8.0/Microsoft.Extensions.FileSystemGlobbing.dll'),('Microsoft.Extensions.FileProviders.Abstractions','6.0.0','lib/net8.0/Microsoft.Extensions.FileProviders.Abstractions.dll'),('Microsoft.Extensions.Primitives','6.0.0','lib/net8.0/Microsoft.Extensions.Primitives.dll')]:
  archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower())
  with zipfile.ZipFile(archive) as z:(stage/(name+'.dll')).write_bytes(z.read(member))
 for p in (source/'src/NuGet.Core/NuGet.Build.Tasks').glob('NuGet*.targets'):shutil.copyfile(p,stage/p.name)
 shutil.copyfile(source/'src/NuGet.Core/NuGet.Build.Tasks/NuGet.props',stage/'NuGet.props')
 resolvers=stage/'SdkResolvers/Microsoft.Build.NuGetSdkResolver';resolvers.mkdir(parents=True,exist_ok=True);shutil.copyfile(stage/'Microsoft.Build.NuGetSdkResolver.dll',resolvers/'Microsoft.Build.NuGetSdkResolver.dll')
feed=prefix/'lib/dotnet/library-packs'
# Each child uses only process-scoped settings and private caches.
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),NUGET_HTTP_CACHE_PATH=native(out/'http-cache'),NUGET_PLUGINS_CACHE_PATH=native(out/'plugins-cache'),NUGET_SCRATCH=native(out/'scratch'),MSBUILDADDITIONALSDKRESOLVERSFOLDER=native(stage/'SdkResolvers'))
def run(label,cmd,expected=0):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 commands.append(dict(label=label,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
fixture=out/'owned Grüsse 世界';fixture.mkdir();ownedfeed=fixture/'feed';ownedfeed.mkdir();payload=fixture/'Payload.dll';cs=fixture/'Payload.cs';cs.write_text('public class Payload { public static string Value => "Grüsse 世界"; }');refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
rsp=fixture/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/out:"'+native(payload)+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(cs)+'"'])+'\n');run('compile-payload',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)])
# Pack requires an actual restore-produced assets file, including the nuspec path.
empty=E.Element('Project');pg=E.SubElement(empty,'PropertyGroup')
for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(fixture/'obj')+'/',BaseIntermediateOutputPath=native(fixture/'obj')+'/',RestoreTaskAssemblyFile=native(stage/'NuGet.Build.Tasks.dll'),NuGetAudit='false',RestoreSources=native(feed)).items():E.SubElement(pg,k).text=v
E.SubElement(empty,'Import',Project=native(stage/'NuGet.targets'));E.ElementTree(empty).write(fixture/'Empty.proj',encoding='utf-8',xml_declaration=True);run('pack-input-restore',[host,stage/'MSBuild.dll',fixture/'Empty.proj','-t:Restore','-nologo','-v:minimal'])
pack=E.Element('Project');E.SubElement(pack,'UsingTask',TaskName='NuGet.Build.Tasks.Pack.PackTask',AssemblyFile=native(stage/'NuGet.Build.Tasks.Pack.dll'));t=E.SubElement(pack,'Target',Name='Pack')
for name,version,dependency in [('Owned.Base','1.0.0',None),('Owned.Top','1.2.3','Owned.Base')]:
 package=E.Element('package');meta=E.SubElement(package,'metadata')
 for k,v in dict(id=name,version=version,authors='Source bootstrap check',description='Owned offline Unicode task fixture').items():E.SubElement(meta,k).text=v
 if dependency:group=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0');E.SubElement(group,'dependency',id=dependency,version='[1.0.0]')
 E.SubElement(E.SubElement(package,'files'),'file',src=native(payload),target='lib/net10.0/Payload.dll');nuspec=fixture/(name+'.nuspec');E.ElementTree(package).write(nuspec,encoding='utf-8',xml_declaration=True)
 E.SubElement(t,'NuGet.Build.Tasks.Pack.PackTask',PackItem=native(nuspec),NuspecFile=native(nuspec),NuspecBasePath=native(fixture),PackageOutputPath=native(ownedfeed),NoPackageAnalysis='true',ContinuePackingAfterGeneratingNuspec='true',Deterministic='true',SymbolPackageFormat='symbols.nupkg',NuspecOutputPath=native(fixture/'nuspec-output'),RestoreOutputPath=native(fixture/'obj'))
E.ElementTree(pack).write(fixture/'Pack.proj',encoding='utf-8',xml_declaration=True);run('pack',[host,stage/'MSBuild.dll',fixture/'Pack.proj','-t:Pack','-nologo','-v:minimal'])
for name in ['Owned.Base.1.0.0.nupkg','Owned.Top.1.2.3.nupkg']:
 with zipfile.ZipFile(ownedfeed/name) as z:assert z.read('lib/net10.0/Payload.dll')==payload.read_bytes()
config=fixture/'NuGet.config';config.write_text('<configuration><packageSources><clear/><add key="owned" value="'+native(ownedfeed)+'"/><add key="installed-source" value="'+native(feed)+'"/></packageSources></configuration>')
def project(folder,package='Owned.Top',version='[1.2.3]'):
 folder.mkdir();p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
 for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(folder/'obj')+'/',BaseIntermediateOutputPath=native(folder/'obj')+'/',RestoreConfigFile=native(config),RestorePackagesPath=native(folder/'cache'),RestoreTaskAssemblyFile=native(stage/'NuGet.Build.Tasks.dll'),NuGetAudit='false').items():E.SubElement(pg,k).text=v
 ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'PackageReference',Include=package,Version=version);E.SubElement(ig,'PackageReference',Include='System.IO.Hashing',Version='[10.0.2]');E.SubElement(p,'Import',Project=native(stage/'NuGet.targets'));path=folder/'Consumer.proj';E.ElementTree(p).write(path,encoding='utf-8',xml_declaration=True);return path
classic=project(fixture/'classic');run('restore',[host,stage/'MSBuild.dll',classic,'-t:Restore','-nologo','-v:minimal'])
def check_assets(folder):
 assets=json.loads((folder/'obj/project.assets.json').read_text());assert set(assets['libraries'])=={'Owned.Top/1.2.3','Owned.Base/1.0.0','System.IO.Hashing/10.0.2'};assert set(assets['targets'])=={'net10.0'}
 for package,version,archive in [('Owned.Top','1.2.3',ownedfeed/'Owned.Top.1.2.3.nupkg'),('Owned.Base','1.0.0',ownedfeed/'Owned.Base.1.0.0.nupkg'),('System.IO.Hashing','10.0.2',feed/'system.io.hashing.10.0.2.nupkg')]:assert (folder/'cache'/package.lower()/version/(package.lower()+'.'+version+'.nupkg')).read_bytes()==archive.read_bytes()
 assert 'lib/net10.0/System.IO.Hashing.dll' in assets['targets']['net10.0']['System.IO.Hashing/10.0.2']['compile']
check_assets(classic.parent)
static=project(fixture/'static');run('static-graph-restore',[host,stage/'NuGet.Build.Tasks.Console.dll','Recursive=true',stage/'MSBuild.dll',static,'RestoreConfigFile='+native(config)]);check_assets(static.parent)
negative=project(fixture/'missing','Owned.Missing','[99.0.0]');run('restore-negative',[host,stage/'MSBuild.dll',negative,'-t:Restore','-nologo','-v:minimal'],1);assert 'NU1101' in (out/'restore-negative.log').read_text(encoding='utf-8')
# Actual MSBuild SDK resolver discovery and imports of an owned local SDK package.
sdkpackage=ownedfeed/'Owned.Sdk.1.0.0.nupkg'
with zipfile.ZipFile(sdkpackage,'w') as z:
 z.writestr('Owned.Sdk.nuspec','<package><metadata><id>Owned.Sdk</id><version>1.0.0</version><authors>Owned</authors><description>Offline SDK resolver fixture</description><packageTypes><packageType name="MSBuildSdk"/></packageTypes></metadata></package>')
 z.writestr('Sdk/Sdk.props','<Project><PropertyGroup><OwnedSdkValue>Grüsse 世界</OwnedSdkValue></PropertyGroup></Project>');z.writestr('Sdk/Sdk.targets','<Project><Target Name="OwnedSdk"><WriteLinesToFile File="$(MSBuildProjectDirectory)/sdk-result.txt" Lines="$(OwnedSdkValue)" Overwrite="true"/></Target></Project>')
sdkproject=fixture/'Sdk.proj';sdkproject.write_text('<Project Sdk="Owned.Sdk/1.0.0"/>');run('sdk-resolver',[host,stage/'MSBuild.dll',sdkproject,'-t:OwnedSdk','-nologo','-v:minimal']);assert (fixture/'sdk-result.txt').read_text(encoding='utf-8-sig').strip()=='Grüsse 世界';assert (out/'cache/owned.sdk/1.0.0/owned.sdk.1.0.0.nupkg').read_bytes()==sdkpackage.read_bytes()
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_pack_task_created_two_packages=True,classic_restore_three_package_graph=True,static_graph_console_restore_three_package_graph=True,original_NET10_assets_and_source_archive_bytes_verified=True,missing_package_rejected_NU1101=True,actual_msbuild_NuGetSdkResolver_discovery_and_imports=True,owned_unicode_sdk_props_targets_passed=True,process_scoped_environment_and_private_caches=True,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original pack and classic/static-graph restore,exact NET10/source assets,NU1101 negative,actual NuGet SDK resolver and Unicode props/targets')
