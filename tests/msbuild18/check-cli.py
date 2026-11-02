"""Stage the source NET10 MSBuild and exercise real CLI/task operations."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as E

plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();stage=out/'stage';stage.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root'])
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
projects=['Microsoft.NET.StringTools','Microsoft.Build.Framework','Microsoft.Build','Microsoft.Build.Utilities.Core','Microsoft.Build.Tasks.Core','MSBuild']
for name in projects:
    for ext in ['dll','pdb']:shutil.copyfile(build/name/(name+'.'+ext),stage/(name+'.'+ext))
versions={'Microsoft.VisualStudio.SolutionPersistence':'1.0.52','System.Configuration.ConfigurationManager':'9.0.11','System.Reflection.MetadataLoadContext':'9.0.11','System.Resources.Extensions':'9.0.11','System.CodeDom':'9.0.11','System.Security.Cryptography.Pkcs':'9.0.11','System.Security.Cryptography.Xml':'9.0.11','System.Diagnostics.EventLog':'9.0.11','System.Security.Cryptography.ProtectedData':'9.0.11','System.Formats.Nrbf':'9.0.11'}
packages={}
for name,version in versions.items():
    package=prefix/'lib/dotnet/library-packs'/(name.lower()+'.'+version+'.nupkg')
    with zipfile.ZipFile(package) as z:
        tfm='net8.0' if name=='Microsoft.VisualStudio.SolutionPersistence' else 'net9.0'
        members=[n for n in z.namelist() if n.startswith('lib/'+tfm+'/') and n.endswith('.dll')]
        windows=[n for n in z.namelist() if n.startswith('runtimes/win/lib/'+tfm+'/') and n.endswith('.dll')]
        for member in members+windows:(stage/Path(member).name).write_bytes(z.read(member))
    packages[name]=dict(version=version,source_package_sha256=sha(package),selected_compile_and_runtime_members=members+windows)
for p in (source/'src/Tasks').iterdir():
    if p.is_file() and p.suffix in {'.props','.targets','.tasks','.overridetasks','.xsd'}:shutil.copyfile(p,stage/p.name)
for name in ['MSBuild.rsp','MSBuild.exe.manifest','Microsoft.Build.xsd']:shutil.copyfile(source/'src/MSBuild'/name,stage/name)
(stage/'MSBuild.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(stage/'MSBuild.dll'),MSBUILDDISABLENODEREUSE='1',MSBUILDUSESERVER='0',MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
def run(label,args):
    command=[host,stage/'MSBuild.dll',*args]
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=result.returncode));assert result.returncode==0,(label,result.returncode)
    return (out/(label+'.log')).read_text(encoding='utf-8')
version=run('version',['-nologo','-version','-noautoresponse']);assert '18.3.0.11413' in version,version
help_text=run('help',['-nologo','-help','-noautoresponse']);assert 'MSBuild' in help_text
work=out/'owned-project';work.mkdir();(work/'input.txt').write_text('Grüße 世界 😀\n',encoding='utf-8')
p=E.Element('Project',DefaultTargets='Build')
for name in ['MakeDir','Copy','ReadLinesFromFile','WriteLinesToFile','Error']:
    E.SubElement(p,'UsingTask',TaskName='Microsoft.Build.Tasks.'+name,AssemblyFile=native(stage/'Microsoft.Build.Tasks.Core.dll'))
pg=E.SubElement(p,'PropertyGroup');E.SubElement(pg,'OwnedDir').text=native(work)
t=E.SubElement(p,'Target',Name='Build');E.SubElement(t,'MakeDir',Directories='$(OwnedDir)/output')
E.SubElement(t,'Copy',SourceFiles='$(OwnedDir)/input.txt',DestinationFiles='$(OwnedDir)/output/copied.txt')
read=E.SubElement(t,'ReadLinesFromFile',File='$(OwnedDir)/output/copied.txt');E.SubElement(read,'Output',TaskParameter='Lines',ItemName='ReadLines')
E.SubElement(t,'Error',Condition="'@(ReadLines)' != 'Grüße 世界 😀'",Text='Unicode task roundtrip failed')
E.SubElement(t,'WriteLinesToFile',File='$(OwnedDir)/receipt.txt',Lines='$(MSBuildVersion)|$(MSBuildAssemblyVersion)|$(MSBuildRuntimeType)',Overwrite='true')
E.ElementTree(p).write(work/'Owned.proj',encoding='utf-8',xml_declaration=True)
run('owned-tasks',[work/'Owned.proj','-nologo','-noautoresponse','-nr:false','-v:minimal'])
assert (work/'output/copied.txt').read_bytes()==(work/'input.txt').read_bytes()
receipt=(work/'receipt.txt').read_text(encoding='utf-8-sig');assert receipt.strip()=='18.3.0|18.0|Core',receipt
properties=run('property-query',[work/'Owned.proj','-nologo','-noautoresponse','-getProperty:MSBuildVersion,MSBuildAssemblyVersion,MSBuildRuntimeType'])
parsed=json.loads(properties);assert parsed['Properties']['MSBuildRuntimeType']=='Core'
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_project_output_sha256={n:sha(stage/(n+'.dll')) for n in projects},source_runtime_packages=packages,actual_cli_version='18.3.0.11413',cli_help_version_json_properties_and_unicode_task_roundtrip_passed=True,source_net10_runtime_execution=True,formal_package_built=False,sdk_style_build_verified=False,parallel_nodes_verified=False,localized_satellites_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS source MSBuild18 CLI version/help,JSON property query and real Unicode file-task build')
