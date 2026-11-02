"""Run MSBuild's pinned original Arcade task and original version override."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E

plan,archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='85d88d61027f75faa8a11fe04c0d1e0572eb3330610f1bb971954f6fb787ec9c'
task_name='src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs';task=out/'CalculateAssemblyAndFileVersions.cs'
with tarfile.open(archive) as t:
    for m in t:
        if m.isfile() and m.name.partition('/')[2]==task_name:task.write_bytes(t.extractfile(m).read())
assert task.is_file()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'))
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',AssemblyName='MSBuild18.VersionTasks').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(task))
for name in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
    r=E.SubElement(ig,'Reference',Include=name);E.SubElement(r,'HintPath').text=native(host.parent/'sdk/8.0.131'/(name+'.dll'));E.SubElement(r,'Private').text='false'
E.ElementTree(p).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True);(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands=[]
def run(label,command):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('build',[host,'build',out/'Build.csproj','-c','Release','--configfile',out/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'])
p=E.Element('Project');E.SubElement(p,'Import',Project=native(source/'eng/Versions.props'))
E.SubElement(p,'UsingTask',TaskName='Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',AssemblyFile=native(out/'bin/Release/net8.0/MSBuild18.VersionTasks.dll'))
t=E.SubElement(p,'Target',Name='_InitializeAssemblyVersion')
vectors=[('1.0.0','20190102.3','1.0.19.5203'),('2.1.800','20190314.5','2.108.19.16405'),('65535.654.9999','20991231.99','65535.65499.9999.63199')]
for index,(version,number,expected) in enumerate(vectors):
    call=E.SubElement(t,'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',VersionPrefix=version,BuildNumber=number)
    E.SubElement(call,'Output',TaskParameter='FileVersion',PropertyName='Vector'+str(index))
    E.SubElement(t,'Error',Condition="'$(Vector"+str(index)+")' != '"+expected+"'",Text='Original upstream version task vector failed')
build_number='20260213.113'
call=E.SubElement(t,'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',VersionPrefix='$(VersionPrefix)',BuildNumber=build_number)
E.SubElement(call,'Output',TaskParameter='FileVersion',PropertyName='FileVersion')
t=E.SubElement(p,'Target',Name='Calculate',DependsOnTargets='_InitializeAssemblyVersion')
E.SubElement(t,'WriteLinesToFile',File=native(out/'file-version.txt'),Lines='$(FileVersion)',Overwrite='true')
E.ElementTree(p).write(out/'Calculate.proj',encoding='utf-8',xml_declaration=True)
run('calculate',[host,'msbuild',out/'Calculate.proj','-t:Calculate','-nologo','-v:minimal'])
version=(out/'file-version.txt').read_text(encoding='utf-8-sig').strip();assert version.startswith('18.3.0.')
(out/'file-version.txt').write_text(version+'\n')
(out/'results.json').write_text(json.dumps(dict(commands=commands,arcade_commit='987d1a73ea67d323c0fc7537bce8ec65d87eb43f',arcade_sdk_version='10.0.0-beta.25578.106',arcade_sdk_vmr_commit='ba5cda19aa70d59758a74b7d36c90e009b32f6f0',arcade_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_task_sha256=hashlib.sha256(task.read_bytes()).hexdigest(),msbuild_original_override_sha256=hashlib.sha256((source/'eng/Versions.props').read_bytes()).hexdigest(),upstream_task_vectors_checked=3,original_task_and_msbuild_override_executed=True,build_number=build_number,build_number_origin='Date/revision decoded from SDK-declared MSBuild18.3.0-release-26113-113;matches original Arcade SemVerV1 date-stamp arithmetic',file_version=version,private_bootstrap_task_framework='net8.0',full_original_toolchain_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS pinned original Arcade task,3 upstream vectors and original MSBuild override:',version)
