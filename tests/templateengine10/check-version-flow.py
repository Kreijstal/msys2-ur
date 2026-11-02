"""Execute the original VMR dependency flow and Arcade import, preserving NuGet6.13.2."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
snapshot,arcade_archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(snapshot)=='e78c80f2a710a26157d7cc95ee62e1dae48cbaa40c3a70d7472c29b461f4cbbb'
assert sha(arcade_archive)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
with tarfile.open(snapshot) as t:t.extractall(out/'snapshot',filter='data')
source=out/'snapshot/templating';arcade=out/'arcade';arcade.mkdir()
with tarfile.open(arcade_archive) as t:
 for m in t:
  if m.isfile() and (m.name.endswith('/tools/DefaultVersions.props') or m.name.endswith('/Microsoft.DotNet.Arcade.Sdk.csproj') or '/eng/' in m.name and m.name.rsplit('/',1)[-1] in ['Versions.props','Version.Details.props']):(arcade/Path(m.name).name).write_bytes(t.extractfile(m).read())
policy=here/'version-flow-policy';manifest=json.loads((policy/'sha256.json').read_text())
for rel,h in manifest['files'].items():assert sha(policy/rel)==h,rel
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';sdk=host.parent/'sdk/8.0.131';p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='VersionFlow',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for n in ['WritePackageVersionsProps.cs','VersionDetailsHelper.cs']:E.SubElement(ig,'Compile',Include=native(policy/'eng/tools/tasks/Microsoft.DotNet.UnifiedBuild.Tasks'/n))
for n in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
 r=E.SubElement(ig,'Reference',Include=n);E.SubElement(r,'HintPath').text=native(sdk/(n+'.dll'))
E.ElementTree(p).write(out/'Flow.csproj',encoding='utf-8',xml_declaration=True);(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='Microsoft.DotNet.UnifiedBuild.Tasks.WritePackageVersionsProps',AssemblyFile=native(out/'bin/Release/net8.0/VersionFlow.dll'));ig=E.SubElement(p,'ItemGroup')
known={'System.CommandLine':'2.0.2',**{n:'10.0.2' for n in ['Microsoft.Extensions.Logging','Microsoft.Extensions.Logging.Abstractions','Microsoft.Extensions.Logging.Console','System.Formats.Asn1']},**{n:'7.3.0-preview.1.11413' for n in ['NuGet.Configuration','NuGet.Credentials','NuGet.Protocol']}}
for name,version in known.items():item=E.SubElement(ig,'KnownPackage',Include=name);E.SubElement(item,'Version').text=version
t=E.SubElement(p,'Target',Name='Write');E.SubElement(t,'Microsoft.DotNet.UnifiedBuild.Tasks.WritePackageVersionsProps',KnownPackages='@(KnownPackage)',OutputPath=native(out/'versions.props'),PropertySuffixes='Version;PackageVersion',VersionPropsFlowType='DependenciesOnly',VersionDetails=native(source/'eng/Version.Details.xml'));E.ElementTree(p).write(out/'Flow.proj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'));commands=[]
def run(label,cmd):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('compile',[host,'build',out/'Flow.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']);run('flow',[host,'msbuild',out/'Flow.proj','-t:Write','-v:minimal','-nologo'])
# Generate the original Arcade defaults file through its own checked-in target.
p=E.Element('Project');E.SubElement(p,'Import',Project=native(arcade/'Versions.props'));pg=E.SubElement(p,'PropertyGroup')
for k,v in {'PackageVersion':'10.0.0-beta.26113.113','_GeneratedVersionFilePath':native(arcade/'DefaultVersions.Generated.props')}.items():E.SubElement(pg,k).text=v
p.append(E.parse(arcade/'Microsoft.DotNet.Arcade.Sdk.csproj').find("Target[@Name='_GenerateSdkVersionFile']"));E.ElementTree(p).write(out/'GenerateDefaults.proj',encoding='utf-8',xml_declaration=True);run('generate-defaults',[host,'msbuild',out/'GenerateDefaults.proj','-t:_GenerateSdkVersionFile','-nologo','-v:minimal'])
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(VersionsPropsPath=native(source/'eng/Versions.props'),DotNetPackageVersionPropsPath=native(out/'versions.props'),DotNetBuildSourceOnly='true').items():E.SubElement(pg,k).text=v
E.SubElement(p,'Import',Project=native(arcade/'DefaultVersions.props'));E.SubElement(p,'Import',Project=native(source/'Directory.Packages.props'));t=E.SubElement(p,'Target',Name='Evaluate');E.SubElement(t,'WriteLinesToFile',File=native(out/'central-versions.txt'),Lines="@(PackageVersion->'%(Identity)=%(Version)')",Overwrite='true');E.ElementTree(p).write(out/'Evaluate.proj',encoding='utf-8',xml_declaration=True);run('evaluate',[host,'msbuild',out/'Evaluate.proj','-t:Evaluate','-nologo','-v:minimal'])
selected=dict(line.split('=',1) for line in (out/'central-versions.txt').read_text(encoding='utf-8-sig').splitlines());expected={**{n:v for n,v in known.items() if not n.startswith('NuGet.')},**{n:'6.13.2' for n in known if n.startswith('NuGet.')}}
for name,version in expected.items():assert selected[name]==version,(name,selected[name],version)
assert 'NuGetConfigurationVersion' not in (out/'versions.props').read_text()
(out/'results.json').write_text(json.dumps(dict(commands=commands,VMR_policy=manifest,original_task_and_Arcade_DefaultVersions_and_central_import_executed=True,Arcade_defaults_generated_by_original_target=True,Arcade_helper_PackageVersion="10.0.0-beta.26113.113",full_Arcade_package_built=False,known_source_packages=known,actual_central_package_versions=selected,original_NuGet6132_requirements_preserved=True,logging_Runtime1002_and_CommandLine202_flow_verified=True,original_Asn1_1002_flow_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS original VMR dependency flow + Arcade import: logging/ASN.1 10.0.2, CommandLine2.0.2; NuGet stays6.13.2')
