"""Evaluate the original VMR NET10 profiles and compile unchanged Arcade helper tasks."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='5a13eccf58c85316c3282bf65de3e53e1adc46f254cac3fc46f0ba7118e3e8d3'
with tarfile.open(archive) as t:t.extractall(out/'snapshot',filter='data')
snapshot=out/'snapshot';source=snapshot/'runtime';libs=source/'src/libraries';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
for rel,h in json.loads((snapshot/'snapshot-sha256.json').read_text()).items():assert sha(snapshot/rel)==h,rel
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';sdk=host.parent/'sdk/8.0.131'
shared=E.Element('Project')
for item in E.parse(libs/'Directory.Build.targets').getroot():
    if item.tag in {'ItemGroup','Choose'} and any(s in E.tostring(item,encoding='unicode') for s in ['NullableAttributes.cs','ExceptionPolyfills.cs','PlatformAttributes.cs','System\\ObsoleteAttribute.cs','System\\Index.cs']):shared.append(copy.deepcopy(item))
E.ElementTree(shared).write(out/'original-shared-sources.targets',encoding='utf-8',xml_declaration=True)
wrappers={};policies={}
for name,original in {'System.IO.Hashing':libs/'System.IO.Hashing/src/System.IO.Hashing.csproj','Microsoft.Extensions.DependencyModel':libs/'Microsoft.Extensions.DependencyModel/src/Microsoft.Extensions.DependencyModel.csproj','Microsoft.NET.HostModel':source/'src/installer/managed/Microsoft.NET.HostModel/Microsoft.NET.HostModel.csproj'}.items():
    folder=out/name;folder.mkdir();tree=E.fromstring(original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/'));tree.attrib.pop('Sdk')
    # This import implements Framework-only PackageDownloadAndReference, unused for NET10.
    for item in list(tree):
        if item.tag=='Import':assert name=='Microsoft.NET.HostModel' and item.get('Project')=='$(RepositoryEngineeringDir)PackageDownloadAndReference.targets';tree.remove(item)
    for item in tree.iter():
        for attr,value in list(item.attrib.items()):
            if item.tag in {'Compile','ProjectReference','EmbeddedResource'} and attr in {'Include','Remove','Update'}:
                value=value.replace('\\','/')
                if not any(s in value for s in ['$(', '@(', '%(']):value=native(original.parent/value)
                item.set(attr,value)
    E.ElementTree(tree).write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
    p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
    props=dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableDefaultCompileItems='false',EnableDefaultEmbeddedResourceItems='false',EnableNETAnalyzers='false',NuGetAudit='false',NetCoreAppCurrent='net10.0',NetCoreAppPrevious='net10.0',NetCoreAppMinimum='net10.0',NetCoreAppToolCurrent='net10.0',NetFrameworkMinimum='',NetFrameworkToolCurrent='',DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',CommonPath=native(libs/'Common/src')+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/',LibrariesProjectRoot=native(libs)+'/',CoreClrProjectRoot=native(source/'src/coreclr')+'/',RepositoryEngineeringDir=native(source/'eng')+'/',DefaultLanguageSourceExtension='.cs',RootNamespace=name,AssemblyName=name,Nullable='enable',CLSCompliant='true' if name!='Microsoft.NET.HostModel' else 'false')
    for k,v in props.items():E.SubElement(pg,k).text=v
    E.SubElement(p,'Import',Project=native(source/'eng/Versions.props'));ig=E.SubElement(p,'ItemGroup')
    if name=='Microsoft.NET.HostModel':
        for group in E.parse(source/'src/installer/Directory.Build.props').getroot():
            if group.tag=='PropertyGroup':p.append(copy.deepcopy(group))
    if name!='System.IO.Hashing':E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**')
    E.SubElement(p,'Import',Project=native(folder/'upstream.proj'));E.SubElement(p,'Import',Project=native(out/'original-shared-sources.targets'))
    resource=original.parent/'Resources/Strings.resx'
    if resource.exists():
        pg=E.SubElement(p,'PropertyGroup');E.SubElement(pg,'StringResourcesPath').text=native(resource);E.SubElement(p,'Import',Project=native(source/'eng/resources.targets'))
    project=folder/(name+'.csproj');E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True);wrappers[name]=native(project);policies[name]=dict(original_project=native(original),original_project_sha256=sha(original),key='Open' if name=='System.IO.Hashing' else 'AspNetCore',resource=native(resource) if resource.exists() else None,cls_compliant=name!='Microsoft.NET.HostModel')
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n');(out/'project-policies.json').write_text(json.dumps(policies,indent=2)+'\n')
# The standalone helper host uses the installed source SDK8. Original tasks are unchanged.
tools=out/'tools';tools.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',AssemblyName='Sdk10.Support.OriginalArcadeTasks').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for name in ['CalculateAssemblyAndFileVersions.cs','GenerateResxSource.cs']:E.SubElement(ig,'Compile',Include=native(snapshot/'arcade'/name))
for name in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
    n=E.SubElement(ig,'Reference',Include=name);E.SubElement(n,'HintPath').text=native(sdk/(name+'.dll'))
E.ElementTree(p).write(tools/'Tasks.csproj',encoding='utf-8',xml_declaration=True)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(here/'EvaluateProjects.cs'))
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    n=E.SubElement(ig,'Reference',Include=name);E.SubElement(n,'HintPath').text=native(sdk/(name+'.dll'))
E.ElementTree(p).write(tools/'Evaluate.csproj',encoding='utf-8',xml_declaration=True);(tools/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false',DOTNET_CLI_HOME=native(tools/'cli-home'),NUGET_PACKAGES=native(tools/'cache'));commands=[]
for label,cmd in [('tasks',[host,'build',tools/'Tasks.csproj','-c','Release','--configfile',tools/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('evaluate-tool',[host,'build',tools/'Evaluate.csproj','-c','Release','--configfile',tools/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal']),('evaluate',[host,tools/'bin/Release/net8.0/Evaluate.dll',out/'wrappers.json',out/'evaluated.json'])]:
    if label=='evaluate':env.update(MSBuildSDKsPath=native(sdk/'Sdks'),MSBUILD_EXE_PATH=native(sdk/'MSBuild.dll'))
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
    commands.append(dict(command=[str(x) for x in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'prepare-results.json').write_text(json.dumps(dict(commands=commands,vmr_commit='44525024595742ebe09023abe709df51de65009b',original_task_source_sha256={p.name:sha(p) for p in (snapshot/'arcade').iterdir()},standalone_original_task_bootstrap_host='net8.0',original_task_full_project_built=False,original_production_source_changes=0),indent=2)+'\n');print('PASS original VMR support project evaluation and original Arcade resource/version helper sources')
