"""Compile exact Immutable8.0.0 original NET8 sources using original Arcade8 version/resource tasks."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,zipfile,xml.etree.ElementTree as E
plan,arcade_archive,out=(Path(p).resolve() for p in sys.argv[1:4]);extra=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None;out.mkdir();here=Path(__file__).resolve().parent;source=plan/'snapshot/runtime';arcade=plan/'snapshot/arcade';model=json.loads((plan/'evaluated.json').read_text());policies=json.loads((plan/'source-inputs.json').read_text())['original_projects'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';sdk=host8.parent/'sdk/8.0.131';compiler=host8.parent/'compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';refs=sorted((host8.parent/'packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll'));assert len(refs)==163
binary=out/'bin';binary.mkdir();records=[];commands=[];outputs={};dependencies=out/'dependency-assets';dependencies.mkdir();assets=[]
assert sha(arcade_archive)=='bf24984501d3647b549b3cd917d92635fc28e2628bc6976e08ed08373c418e29'
arcade=out/'arcade';arcade.mkdir()
with tarfile.open(arcade_archive) as t:
 for m in t:
  if m.isfile() and m.name.rsplit('/',1)[-1] in ['CalculateAssemblyAndFileVersions.cs','GenerateResxSource.cs','Version.BeforeCommonTargets.targets']:(arcade/Path(m.name).name).write_bytes(t.extractfile(m).read())
def run(label,cmd,folder,hostroot):
    env=dict(os.environ,DOTNET_ROOT=native(hostroot),DOTNET_ROOT_X64=native(hostroot),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
    commands.append(dict(label=label,command=[str(x) for x in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
tools=out/'tools';tools.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='Extensions10.OriginalTasks',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for n in ['CalculateAssemblyAndFileVersions.cs','GenerateResxSource.cs']:E.SubElement(ig,'Compile',Include=native(arcade/n))
for n in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
 r=E.SubElement(ig,'Reference',Include=n);E.SubElement(r,'HintPath').text=native(sdk/(n+'.dll'))
E.ElementTree(p).write(tools/'Tasks.csproj',encoding='utf-8',xml_declaration=True);(tools/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>');run('tasks',[host8,'build',tools/'Tasks.csproj','-c','Release','--configfile',tools/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'],tools,host8.parent);helper=tools/'bin/Release/net8.0/Extensions10.OriginalTasks.dll'
for name,entry in model.items():
    folder=out/name;folder.mkdir();props=entry['properties'];policy=policies[name];tfm=policy['framework'];assert props['TargetFramework']==tfm;isgen=policy['generator'];selected_refs={p.name:p for p in (nsrefs if isgen else refs)}
    selected_refs.pop(name+'.dll',None)
    edges=[]
    for edge in entry['items']['ProjectReference']:
        dep=Path(edge['full_path']).stem;edges.append(dict(project=dep,metadata=edge['metadata']))
        if edge['metadata'].get('ReferenceOutputAssembly','true').lower()=='false':continue
        assert dep+'.dll' in selected_refs,dep
    # Propagate NET10 project-reference closure, retaining the generator's ReferenceOutputAssembly=false edge.
    if not isgen:
        for dep,file in outputs.items():
            if policies[dep]['framework']=='net8.0':selected_refs[file.name]=file
    files=list(dict.fromkeys(Path(p['full_path']).resolve() for p in entry['items']['Compile']));assert files and all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files}
    key=bytes.fromhex((here/'Microsoft.pubkey.hex').read_text());(folder/'public.snk').write_bytes(key);token=hashlib.sha1(key).digest()[-8:][::-1].hex();assert token=='b03f5f7f11d50a3a'
    p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
    for k,v in dict(MajorVersion='8',MinorVersion='0',PatchVersion='0',PreReleaseVersionLabel='servicing',DotNetFinalVersionKind='release',OfficialBuild='true',OfficialBuildId='20231031.3',IsShipping='true').items():E.SubElement(pg,k).text=v
    E.SubElement(p,'Import',Project=native(arcade/'Version.BeforeCommonTargets.targets'))
    for task in ['CalculateAssemblyAndFileVersions','GenerateResxSource']:E.SubElement(p,'UsingTask',TaskName='Microsoft.DotNet.Arcade.Sdk.'+task,AssemblyFile=native(helper))
    E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(sdk/'Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(p,'Target',Name='Generate')
    task=E.SubElement(target,'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',VersionPrefix='$(VersionPrefix)',BuildNumber='$(OfficialBuildId)');E.SubElement(task,'Output',TaskParameter='FileVersion',PropertyName='FV');E.SubElement(task,'Output',TaskParameter='AssemblyVersion',PropertyName='AV');E.SubElement(target,'WriteLinesToFile',File=native(folder/'versions.txt'),Lines='$(Version);$(AV);$(FV)',Overwrite='true')
    resources=[];generated=[]
    for item in entry['items']['EmbeddedResource']:
        resx=Path(item['full_path']).resolve();logical=item['metadata']['ManifestResourceName'];assert resx.suffix=='.resx'
        generated_file=folder/'SR.Generated.cs';generated.append(generated_file)
        E.SubElement(target,'Microsoft.DotNet.Arcade.Sdk.GenerateResxSource',Language='C#',ResourceFile=native(resx),ResourceName=logical,ResourceClassName=item['metadata']['ClassName'],OmitGetResourceString='true',OutputPath=native(generated_file))
        resource=folder/'Strings.resources';E.SubElement(target,'GenerateResource',Sources=native(resx),OutputResources=native(resource),ExecuteAsTool='false');resources.append((resx,resource,logical+'.resources'))
    E.ElementTree(p).write(folder/'Generate.proj',encoding='utf-8',xml_declaration=True);run(name+'-generate',[host8,'msbuild',folder/'Generate.proj','-t:Generate','-nologo','-v:minimal'],folder,host8.parent)
    version,calculated_assembly,fileversion=(folder/'versions.txt').read_text(encoding='utf-8-sig').splitlines();expected='8.0.0';assert version==expected,(name,version);assert fileversion=='8.0.23.53103'
    assembly_version=props['AssemblyVersion'] or calculated_assembly
    assert assembly_version=='8.0.0.0',(name,assembly_version)
    attrs=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(assembly_version)+')]','[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(fileversion)+')]','[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps(version+'+source-runtime.5535e31a712343a63f5d7d796cd874e563e5ac14')+')]','[assembly:System.Runtime.Versioning.TargetFramework('+json.dumps('.NETStandard,Version=v2.0' if isgen else '.NETCoreApp,Version=v8.0')+')]']
    if props['CLSCompliant'].lower()=='true':attrs.append('[assembly:System.CLSCompliant(true)]')
    if resources and not any('NeutralResourcesLanguage(' in f.read_text(encoding='utf-8-sig') for f in files):attrs.append('[assembly:System.Resources.NeutralResourcesLanguage("en-US")]')
    for item in entry['items']['InternalsVisibleTo']:attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+key.hex())+')]')
    info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');files+=generated+[info]
    defines=list(dict.fromkeys(props['DefineConstants'].replace(',',';').split(';')+(['TRACE','NET','NETCOREAPP','NET8_0',*['NET'+str(i)+'_0_OR_GREATER' for i in range(5,9)],*['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]] if not isgen else ['TRACE','NETSTANDARD','NETSTANDARD2_0','NETSTANDARD2_0_OR_GREATER','NETSTANDARD1_0_OR_GREATER','NETSTANDARD1_1_OR_GREATER','NETSTANDARD1_2_OR_GREATER','NETSTANDARD1_3_OR_GREATER','NETSTANDARD1_4_OR_GREATER','NETSTANDARD1_5_OR_GREATER','NETSTANDARD1_6_OR_GREATER'])))
    destination=binary/(name+'.dll');args=['/nostdlib+','/target:library','/langversion:preview','/nullable:'+(props['Nullable'] or 'disable'),'/unsafe'+('+' if props['AllowUnsafeBlocks'].lower()=='true' else '-'),'/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(folder/'public.snk')+'"','/out:"'+native(destination)+'"','/define:'+';'.join(d for d in defines if d)]
    if props['GenerateDocumentationFile'].lower()=='true':args.append('/doc:"'+native(destination.with_suffix('.xml'))+'"')
    if props['NoWarn']:args.append('/nowarn:'+props['NoWarn'].replace(';',','))
    if props['TreatWarningsAsErrors'].lower()=='true':args.append('/warnaserror+')
    args+=['/reference:"'+native(p)+'"' for p in selected_refs.values()]+['/resource:"'+native(resource)+'",'+logical for resx,resource,logical in resources]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)],folder,host.parent)
    record=dict(assembly=name,version=version,assembly_version=assembly_version,file_version=fileversion,public_key_token=token,original_framework=tfm,original_project_edges=edges,original_source_sha256=originals,original_resource_sha256={resx.relative_to(source).as_posix():sha(resx) for resx,_,_ in resources},generated_source_sha256={native(p):sha(p) for p in generated},original_reference_sha256={native(p):sha(p) for p in selected_refs.values()},output_sha256={ext:sha(destination.with_suffix('.'+ext)) for ext in (['dll','pdb','xml'] if props['GenerateDocumentationFile'].lower()=='true' else ['dll','pdb'])},original_project_sha256=policy['original_project_sha256'],original_resources={r.relative_to(source).as_posix():dict(sha256=sha(r),logical_name=logical.removesuffix('.resources')) for r,_,logical in resources},key_policy='Microsoft',original_production_source_changes=0)
    outputs[name]=destination;records.append(record);(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,version,assembly_version,fileversion,len(originals),'original release inputs',flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,dependency_assets=assets,source_commit='5535e31a712343a63f5d7d796cd874e563e5ac14',original_arcade_version_and_resource_tasks_executed=True,original_official_build_id='20231031.3',other_original_framework_profiles_built=False,formal_packages_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
