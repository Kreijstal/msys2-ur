"""Build the next original NET10 NuGet closure using installed source foundations."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as E

plan,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);model=json.loads((plan/'evaluated.json').read_text());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));records=[];outputs={};commands=[]
binary=out/'bin';binary.mkdir();dependencies=out/'dependency-assets';dependencies.mkdir()
def run(folder,label,command,environment=env):
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
feed=prefix/'lib/dotnet/library-packs';dependency_records=[];transitive={}
def package_asset(package,version,member,destination):
    archive=next(p for p in feed.iterdir() if p.name.lower()==f'{package}.{version}.nupkg'.lower())
    with zipfile.ZipFile(archive) as z:destination.write_bytes(z.read(member))
    dependency_records.append(dict(package=package,version=version,archive=native(archive),archive_sha256=sha(archive),member=member,output=native(destination),output_sha256=sha(destination)))
    return destination
foundations=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel','NuGet.Configuration','NuGet.Packaging','NuGet.Protocol','NuGet.DependencyResolver.Core','NuGet.ProjectModel','NuGet.Credentials','NuGet.Resolver','NuGet.Commands']
for name in foundations:
    outputs[name]=package_asset(name,'7.3.0-preview.1.11413','lib/net10.0/'+name+'.dll',dependencies/(name+'.dll'))
    transitive[name]=[]
for name in foundations:
    def walk(project):
        for item in model[project]['items']['ProjectReference']:
            dep=Path(item['full_path']).stem
            yield outputs[dep]
            yield from walk(dep)
    transitive[name]=list(walk(name))
external={}
for name,version,member in [
    ('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll'),
    ('System.Security.Cryptography.Pkcs','8.0.1','ref/net8.0/System.Security.Cryptography.Pkcs.dll'),
    ('Microsoft.Extensions.FileSystemGlobbing','6.0.0','ref/net8.0/Microsoft.Extensions.FileSystemGlobbing.dll'),
    ('Microsoft.Extensions.FileProviders.Abstractions','6.0.0','ref/net8.0/Microsoft.Extensions.FileProviders.Abstractions.dll'),
    ('Microsoft.Extensions.Primitives','6.0.0','ref/net8.0/Microsoft.Extensions.Primitives.dll')]:
    external[name]=package_asset(name,version,member,dependencies/(name+'.dll'))
external['Newtonsoft.Json']=package_asset('Newtonsoft.Json','13.0.3','lib/netstandard2.0/Newtonsoft.Json.dll',dependencies/'Newtonsoft.Json.dll')
msbuild=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap'
for name in ['Microsoft.Build','Microsoft.Build.Framework','Microsoft.Build.Tasks.Core','Microsoft.Build.Utilities.Core','Microsoft.NET.StringTools']:
    external[name]=msbuild/(name+'.dll');assert external[name].is_file();dependency_records.append(dict(package=name,version='18.3.0-release-26113-113',source_installed_bootstrap=native(msbuild),output=native(external[name]),output_sha256=sha(external[name])))
names=['NuGet.Build.Tasks.Pack','NuGet.Build.Tasks','NuGet.Build.Tasks.Console','Microsoft.Build.NuGetSdkResolver']
for name in names:
    entry=model[name];props=entry['properties'];assert props['MicrosoftBuildVersion']=='18.3.0-release-26113-113';assert props['TargetFramework']==props['TargetFrameworks']=='net10.0';assert props['Version']=='7.3.0-preview.1.11413';assert props['AssemblyVersion']=='7.3.0.0' and props['FileVersion']=='7.3.0.11413'
    folder=out/name
    folder.mkdir();files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']));assert all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files};references=list(refs)+list(external.values())
    for item in entry['items']['ProjectReference']:
        dep=Path(item['full_path']).stem;assert dep in outputs,dep;references.append(outputs[dep])
        references.extend(transitive[dep])
    for item in entry['items']['PackageReference']:
        dep=item['identity'];assert dep in external,dep;references.append(external[dep])
        if dep=='Microsoft.Extensions.FileProviders.Abstractions':references.append(external['Microsoft.Extensions.Primitives'])
    transitive[name]=references[len(refs):]
    unique={}
    for ref in references:
        if ref.name in unique:assert sha(ref)==sha(unique[ref.name]),ref.name
        else:unique[ref.name]=ref
    references=list(unique.values())
    p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(p,'Target',Name='Generate');resources=[];resource_inputs={}
    project_folder=source/'src/NuGet.Core'/name
    for item in entry['items']['EmbeddedResource']:
        resx=Path(item['full_path']).resolve();resource_inputs[resx.relative_to(source).as_posix()]=sha(resx)
        if resx.suffix!='.resx':
            link=item['metadata'].get('LogicalName') or name+'.'+item['metadata'].get('Link',resx.relative_to(project_folder).as_posix()).replace('/','.').replace('\\','.')
            resources.append((resx,link));continue
        logical=name+'.'+resx.relative_to(project_folder).with_suffix('').as_posix().replace('/','.')+'.resources';output=folder/logical
        E.SubElement(target,'GenerateResource',Sources=native(resx),OutputResources=native(output),ExecuteAsTool='false');resources.append((output,logical))
    E.ElementTree(p).write(folder/'Resources.proj',encoding='utf-8',xml_declaration=True)
    run(folder,name+'-resources',[host8,'msbuild',folder/'Resources.proj','-t:Generate','-nologo'],dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent)))
    key=Path(props['AssemblyOriginatorKeyFile']);assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
    attrs=['[assembly:System.Reflection.AssemblyVersion("7.3.0.0")]','[assembly:System.Reflection.AssemblyFileVersion("7.3.0.11413")]','[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps(props['InformationalVersion'])+')]','[assembly:System.Resources.NeutralResourcesLanguage("en-US")]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]']
    for item in entry['items']['InternalsVisibleTo']:
        key=item['metadata'].get('PublicKey');assert key
        attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+key)+')]')
    info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');files.append(info)
    defines=list(dict.fromkeys(props['DefineConstants'].split(';')+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]+['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]));assert 'DEBUG' not in defines and 'IS_CORECLR' in defines
    destination=binary/(name+'.dll');args=['/nostdlib+','/target:'+('exe' if props['OutputType']=='Exe' else 'library'),'/langversion:preview','/nullable:enable','/optimize+','/unsafe+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(Path(props['AssemblyOriginatorKeyFile']))+'"','/out:"'+native(destination)+'"','/define:'+';'.join(defines)]
    if props['GenerateDocumentationFile']!='false':args.append('/doc:"'+native(destination.with_suffix('.xml'))+'"')
    if props['ApplicationManifest']:args.append('/win32manifest:"'+native(project_folder/props['ApplicationManifest'])+'"')
    args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
    generators=[]
    if any('JsonSerializerContext' in p.read_text(encoding='utf-8-sig') for p in files):
        generator=prefix/'lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs/System.Text.Json.SourceGeneration.dll'
        assert generator.is_file();generators.append(generator);args.append('/analyzer:"'+native(generator)+'"')
        generated=folder/'generated';generated.mkdir();args.append('/generatedfilesout:"'+native(generated)+'"')
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(folder,name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)])
    records.append(dict(assembly=name,original_target='net10.0',original_source_sha256=originals,original_resource_sha256=resource_inputs,actual_reference_sha256={native(p):sha(p) for p in references},source_generators_sha256={native(p):sha(p) for p in generators},output_sha256=sha(destination),output_assets_sha256={p.suffix[1:]:sha(p) for p in [destination,destination.with_suffix('.pdb'),destination.with_suffix('.xml')] if p.exists()},original_version=props['Version'],assembly_version=props['AssemblyVersion'],file_version=props['FileVersion'],original_production_source_changes=0,declared_package_references=entry['items']['PackageReference']))
    if props['OutputType']=='Exe':destination.with_suffix('.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net10.0','rollForward':props['RollForward'] or 'LatestMajor','framework':{'name':'Microsoft.NETCore.App','version':'10.0.5'},'configProperties':{'System.GC.Server':props['ServerGarbageCollection']=='true'}}}))
    outputs[name]=destination;(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,len(originals),'unchanged original source inputs',flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,dependency_assets=dependency_records,installed_source_foundations_reused=foundations,original_vmr_dependency_version_flow_executed=True,original_vmr_net10_profile=True,formal_package_built=False,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
