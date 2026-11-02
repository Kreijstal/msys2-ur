"""Restore the original TemplateEngine NET10 central package graph from source archives."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,out=(Path(p).resolve() for p in sys.argv[1:3]);candidate=Path(sys.argv[3]).resolve() if len(sys.argv)>3 and sys.argv[3]!='--strict' else None;strict='--strict' in sys.argv;out.mkdir();native=lambda p:Path(p).resolve().as_posix();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);model=json.loads((plan/'evaluated.json').read_text());prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';tools=prefix/'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin';feed=prefix/'lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/>'+('<add key="candidate-source" value="'+native(candidate/'lib/dotnet/library-packs')+'"/>' if candidate else '')+'<add key="installed-source" value="'+native(feed)+'"/></packageSources></configuration>');p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',ManagePackageVersionsCentrally='true',CentralPackageVersionsFileImported='true',CentralPackageTransitivePinningEnabled='true',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(out/'obj')+'/',BaseIntermediateOutputPath=native(out/'obj')+'/',RestoreConfigFile=native(out/'NuGet.config'),RestorePackagesPath=native(out/'cache'),RestoreTaskAssemblyFile=native(tools/'NuGet.Build.Tasks.dll'),NuGetAudit='false').items():E.SubElement(pg,k).text=v
E.SubElement(pg,'TreatWarningsAsErrors').text='true' if strict else 'false'
ig=E.SubElement(p,'ItemGroup');central={};direct=set()
for name,m in model.items():
 for i in m['items']['PackageVersion']:
  if i['metadata'].get('Version'):
   version=i['metadata']['Version'];assert i['identity'] not in central or central[i['identity']]==version;central[i['identity']]=version
 for i in m['items']['PackageReference']:direct.add(i['identity'])
for name,version in central.items():E.SubElement(ig,'PackageVersion',Include=name,Version=version)
for name in sorted(direct):E.SubElement(ig,'PackageReference',Include=name)
E.SubElement(p,'Import',Project=native(tools/'NuGet.targets'));E.ElementTree(p).write(out/'Restore.proj',encoding='utf-8',xml_declaration=True);cmd=[host,tools/'MSBuild.dll',out/'Restore.proj','-t:Restore','-nologo','-v:minimal']
with (out/'restore.log').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache')),timeout=180)
record=dict(command=[str(p) for p in cmd],exit_code=r.returncode,original_central_package_transitive_pinning_enabled=True,original_TreatWarningsAsErrors_applied=strict,full_original_SDK_pruning_integration_verified=False,original_direct_package_requirements={n:central[n] for n in sorted(direct)},original_all_central_versions=central,full_dependency_goal_complete=False)
if (out/'obj/project.assets.json').exists():
 assets=json.loads((out/'obj/project.assets.json').read_text());record['diagnostics']=assets.get('logs',[]);record['selected_packages']=list(assets['libraries']);record['original_untouched_central_requirements']=True
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print((out/'restore.log').read_text());raise SystemExit(r.returncode)
