"""Compile three exact original VMR NET10 runtime support profiles."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;source=plan/'snapshot/runtime';arcade=plan/'snapshot/arcade';model=json.loads((plan/'evaluated.json').read_text());policies=json.loads((plan/'project-policies.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';sdk=host8.parent/'sdk/8.0.131';compiler=host8.parent/'compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';refs=sorted((host8.parent/'reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
helper=plan/'tools/bin/Release/net8.0/Sdk10.Support.OriginalArcadeTasks.dll';binary=out/'bin';binary.mkdir();records=[];commands=[]
def run(label,cmd,folder,hostroot):
    env=dict(os.environ,DOTNET_ROOT=native(hostroot),DOTNET_ROOT_X64=native(hostroot),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
    commands.append(dict(label=label,command=[str(x) for x in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
for name,entry in model.items():
    folder=out/name;folder.mkdir();props=entry['properties'];policy=policies[name];assert props['TargetFramework']=='net10.0';assert not entry['items']['ProjectReference'] and not entry['items']['PackageReference']
    files=list(dict.fromkeys(Path(p['full_path']).resolve() for p in entry['items']['Compile']));assert files and all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files}
    key=bytes.fromhex((here/(policy['key']+'.pubkey.hex')).read_text());(folder/'public.snk').write_bytes(key);token=hashlib.sha1(key).digest()[-8:][::-1].hex();assert token==('cc7b13ffcd2ddd51' if policy['key']=='Open' else 'adb9793829ddae60')
    p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
    for k,v in dict(MajorVersion='10',MinorVersion='0',PatchVersion='2',PreReleaseVersionLabel='servicing',DotNetFinalVersionKind='release',OfficialBuild='true',OfficialBuildId='20251212.105',IsShipping='false' if name=='Microsoft.NET.HostModel' else 'true').items():E.SubElement(pg,k).text=v
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
    version,calculated_assembly,fileversion=(folder/'versions.txt').read_text(encoding='utf-8-sig').splitlines();expected='10.0.2-servicing.25612.105' if name=='Microsoft.NET.HostModel' else '10.0.2';assert version==expected,(name,version);assert fileversion=='10.0.225.61305'
    assembly_version=props['AssemblyVersion'] or calculated_assembly
    assert assembly_version==('10.0.2.0' if name=='Microsoft.NET.HostModel' else '10.0.0.0'),(name,assembly_version)
    attrs=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(assembly_version)+')]','[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(fileversion)+')]','[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps(version+'+source-vmr.44525024595742ebe09023abe709df51de65009b')+')]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]']
    if policy['cls_compliant']:attrs.append('[assembly:System.CLSCompliant(true)]')
    if resources:attrs.append('[assembly:System.Resources.NeutralResourcesLanguage("en-US")]')
    for item in entry['items']['InternalsVisibleTo']:attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+key.hex())+')]')
    info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');files+=generated+[info]
    defines=list(dict.fromkeys(props['DefineConstants'].replace(',',';').split(';')+['TRACE','NET','NETCOREAPP','NET10_0',*['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)],*['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]]))
    destination=binary/(name+'.dll');args=['/nostdlib+','/target:library','/langversion:preview','/nullable:enable','/unsafe+','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(folder/'public.snk')+'"','/out:"'+native(destination)+'"','/doc:"'+native(destination.with_suffix('.xml'))+'"','/define:'+';'.join(d for d in defines if d)]
    args+=['/reference:"'+native(p)+'"' for p in refs]+['/resource:"'+native(resource)+'",'+logical for resx,resource,logical in resources]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)],folder,host.parent)
    record=dict(assembly=name,version=version,assembly_version=assembly_version,file_version=fileversion,public_key_token=token,original_framework='net10.0',original_source_sha256=originals,original_resource_sha256={resx.relative_to(source).as_posix():sha(resx) for resx,_,_ in resources},generated_source_sha256={native(p):sha(p) for p in generated},original_reference_sha256={native(p):sha(p) for p in refs},output_sha256={ext:sha(destination.with_suffix('.'+ext)) for ext in ['dll','pdb','xml']},original_project_sha256=policy['original_project_sha256'],original_production_source_changes=0)
    records.append(record);(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,version,assembly_version,fileversion,len(originals),'original VMR inputs',flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,vmr_commit='44525024595742ebe09023abe709df51de65009b',original_arcade_version_and_resource_tasks_executed=True,original_official_build_id='20251212.105',other_original_framework_profiles_built=False,formal_packages_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
