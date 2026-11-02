"""Compile original NET10 TemplateEngine profiles and original resource/version tasks."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tarfile,xml.etree.ElementTree as E
plan,arcade_archive,restored,out=(Path(p).resolve() for p in sys.argv[1:5]);reuse=None;out.mkdir();here=Path(__file__).resolve().parent;source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);model=json.loads((plan/'evaluated.json').read_text());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(arcade_archive)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66';arcade=out/'arcade';arcade.mkdir()
wanted=['src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs','src/Microsoft.DotNet.Arcade.Sdk/src/GenerateResxSource.cs','src/Microsoft.DotNet.Arcade.Sdk/tools/Version.BeforeCommonTargets.targets']
with tarfile.open(arcade_archive) as t:
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and rel in wanted:(arcade/Path(rel).name).write_bytes(t.extractfile(m).read())
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';sdk=host8.parent/'sdk/8.0.131';compiler=host8.parent/'compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';framework=sorted((host8.parent/'reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(framework)==167
binary=out/'bin';binary.mkdir();dependencies=out/'dependency-assets';dependencies.mkdir();feed=prefix/'lib/dotnet/library-packs';commands=[];assets=[];records=[];outputs={}
def run(label,cmd,folder,root,expected=0):
    env=dict(os.environ,DOTNET_ROOT=native(root),DOTNET_ROOT_X64=native(root),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'empty-cache'))
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=240)
    commands.append(dict(label=label,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
# Unchanged original Arcade task sources in a standalone source SDK8 host.
tools=out/'tools';tools.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',AssemblyName='Sdk10.OriginalTasks',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup')
for n in ['CalculateAssemblyAndFileVersions.cs','GenerateResxSource.cs']:E.SubElement(ig,'Compile',Include=native(arcade/n))
for n in ['Microsoft.Build.Framework','Microsoft.Build.Utilities.Core','NuGet.Versioning']:
    e=E.SubElement(ig,'Reference',Include=n);E.SubElement(e,'HintPath').text=native(sdk/(n+'.dll'))
E.ElementTree(p).write(tools/'Build.csproj',encoding='utf-8',xml_declaration=True);(tools/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>');run('tools',[host8,'build',tools/'Build.csproj','-c','Release','--configfile',tools/'NuGet.config','-p:UseSharedCompilation=false','-v:minimal'],tools,host8.parent);helper=tools/'bin/Release/net8.0/Sdk10.OriginalTasks.dll'
import zipfile
external={}
def extract(name,version,member):
    archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower());destination=dependencies/Path(member).name
    with zipfile.ZipFile(archive) as z:destination.write_bytes(z.read(member))
    assets.append(dict(id=name,version=version,archive=native(archive),archive_sha256=sha(archive),member=member,output=native(destination),output_sha256=sha(destination)));external[name]=destination
restore=json.loads((restored/'obj/project.assets.json').read_text())
for identity,meta in restore['libraries'].items():
    name,version=identity.split('/');members=[m for m in restore['targets']['net10.0'][identity].get('compile',{}) if m.endswith('.dll')]
    if not members:continue
    assert len(members)==1,(name,members)
    cached=restored/'cache'/name.lower()/version/(name.lower()+'.'+version+'.nupkg')
    # Candidate ASN.1 and installed source archives are the only restore feeds.
    installed=next((p for p in feed.iterdir() if p.name.lower()==cached.name),None)
    if installed:assert cached.read_bytes()==installed.read_bytes(),identity
    with zipfile.ZipFile(cached) as z:
        member=members[0];destination=dependencies/Path(member).name;destination.write_bytes(z.read(member))
    external[name]=destination;assets.append(dict(id=name,version=version,archive=native(cached),archive_sha256=sha(cached),member=member,output=native(destination),output_sha256=sha(destination)))
for name,entry in model.items():
    folder=out/name;folder.mkdir();props=entry['properties'];
    versions={i['identity']:i['metadata'].get('Version') for i in entry['items']['PackageVersion']}
    supplied={i['id']:i.get('version',i.get('declared_package_version')) for i in assets}
    for item in entry['items']['PackageReference']:
        expected=versions[item['identity']]
        if item['identity']=='Microsoft.Build.Runtime':assert expected=='18.3.0-release-26113-113'
        else:assert supplied[item['identity']]==expected,(name,item['identity'],expected,supplied.get(item['identity']))
    assert props['TargetFramework']=='net10.0';files=list(dict.fromkeys(Path(p['full_path']).resolve() for p in entry['items']['Compile']));assert files and all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files};refs={p.name:p for p in framework};aliases=[]
    # Explicit complete package closure mirrors SDK compile-time reference propagation.
    for p in external.values():refs[p.name]=p
    edges=[]
    for item in entry['items']['ProjectReference']:
        dep=Path(item['full_path']).stem;assert dep in outputs,dep;edges.append(dict(assembly=dep,metadata=item['metadata']))
        if item['metadata'].get('ReferenceOutputAssembly','true').lower()=='false':continue
        alias=item['metadata'].get('Aliases')
        if alias:aliases.append((alias,outputs[dep]))
        else:refs[dep+'.dll']=outputs[dep]
    # Propagate the original project reference closure through previously built NET10 projects.
    for dep,file in outputs.items():refs[file.name]=file
    if reuse is not None:
        old=next((p for p in json.loads((reuse/'progress.json').read_text()) if p['assembly']==name),None)
        if old:
            assert old['original_source_sha256']==originals
            assert {Path(p).name:h for p,h in old['actual_reference_sha256'].items()}=={p.name:sha(p) for p in refs.values()}
            for ext,h in old['output_sha256'].items():assert sha(reuse/'bin'/(name+'.'+ext))==h;shutil.copyfile(reuse/'bin'/(name+'.'+ext),binary/(name+'.'+ext))
            shutil.copytree(reuse/name,folder,dirs_exist_ok=True);outputs[name]=binary/(name+'.dll');records.append(old);print('REUSE verified',name,flush=True);continue
    p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
    E.SubElement(p,'Import',Project=native(source/'eng/Versions.props'))
    for k,v in dict(OfficialBuild='true',OfficialBuildId='20260213.113',DotNetFinalVersionKind='',IsShipping='true').items():E.SubElement(pg,k).text=v
    E.SubElement(p,'Import',Project=native(arcade/'Version.BeforeCommonTargets.targets'))
    for task in ['GenerateResxSource','CalculateAssemblyAndFileVersions']:E.SubElement(p,'UsingTask',TaskName='Microsoft.DotNet.Arcade.Sdk.'+task,AssemblyFile=native(helper))
    E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(sdk/'Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(p,'Target',Name='Generate');resources=[];generated=[];resource_inputs={}
    for index,item in enumerate(entry['items']['EmbeddedResource']):
        resx=Path(item['full_path']).resolve();meta=item['metadata'];namespace=meta.get('Namespace');project_dir=source/'src'/name;logical=meta.get('ManifestResourceName') or (namespace+'.'+resx.stem if namespace else props['RootNamespace']+'.'+resx.relative_to(project_dir).with_suffix('').as_posix().replace('/','.'));classname=meta.get('ClassName') or logical;generated_file=folder/('Resources'+str(index)+'.g.cs');output=folder/('Resources'+str(index)+'.resources')
        E.SubElement(target,'Microsoft.DotNet.Arcade.Sdk.GenerateResxSource',Language='C#',ResourceFile=native(resx),ResourceName=logical,ResourceClassName=classname,OutputPath=native(generated_file));E.SubElement(target,'GenerateResource',Sources=native(resx),OutputResources=native(output),ExecuteAsTool='false');resources.append((output,logical+'.resources'));generated.append(generated_file);resource_inputs[resx.relative_to(source).as_posix()]=dict(sha256=sha(resx),logical_name=logical)
    call=E.SubElement(target,'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions',VersionPrefix='$(VersionPrefix)',BuildNumber='$(OfficialBuildId)',PatchNumber='$(_PatchNumber)',AutoGenerateAssemblyVersion=props['AutoGenerateAssemblyVersion'] or 'false');E.SubElement(call,'Output',TaskParameter='AssemblyVersion',PropertyName='AV');E.SubElement(call,'Output',TaskParameter='FileVersion',PropertyName='FV');E.SubElement(target,'WriteLinesToFile',File=native(folder/'versions.txt'),Lines='$(Version);$(AV);$(FV)',Overwrite='true');E.ElementTree(p).write(folder/'Generate.proj',encoding='utf-8',xml_declaration=True);run(name+'-generate',[host8,'msbuild',folder/'Generate.proj','-t:Generate','-nologo','-v:minimal'],folder,host8.parent)
    package_version,assembly_version,file_version=(folder/'versions.txt').read_text(encoding='utf-8-sig').splitlines();assert package_version=='10.0.200-preview.26113.113',(name,package_version);keyname=props['StrongNameKeyId'];assert keyname in ['MicrosoftShared','MicrosoftAspNetCore'];key=bytes.fromhex((here/(keyname+'.pubkey.hex')).read_text());(folder/'public.snk').write_bytes(key)
    attrs=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(assembly_version)+')]','[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(file_version)+')]','[assembly:System.Reflection.AssemblyInformationalVersion("10.0.200-preview.26113.113+source-vmr.05d9490471fb4b10d7ef4faa32c423e1b5adcaee")]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]']
    if resources:attrs.append('[assembly:System.Resources.NeutralResourcesLanguage("en-US")]')
    for item in entry['items']['InternalsVisibleTo']:attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+item['metadata'].get('Key',item['metadata'].get('PublicKey',key.hex())))+')]')
    info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');usings=folder/'GlobalUsings.g.cs';usings.write_text('\n'.join('global using '+p['identity']+';' for p in entry['items']['Using'])+'\n');files+=generated+[info,usings]
    defines=list(dict.fromkeys(props['DefineConstants'].replace(',',';').split(';')+['NET','NETCOREAPP','NET10_0',*['NETCOREAPP'+v+'_OR_GREATER' for v in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']],*['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]]));destination=binary/(name+'.dll');args=['/nostdlib+','/target:library','/nullable:'+(props['Nullable'] or 'disable'),'/langversion:preview','/unsafe'+('+' if props['AllowUnsafeBlocks'].lower()=='true' else '-'),'/optimize'+('+' if props['Optimize'].lower()=='true' else '-'),'/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(folder/'public.snk')+'"','/out:"'+native(destination)+'"','/define:'+';'.join(d for d in defines if d)]
    if props['GenerateDocumentationFile'].lower()=='true':args.append('/doc:"'+native(destination.with_suffix('.xml'))+'"')
    if props['WarningLevel']:args.append('/warn:'+props['WarningLevel'])
    for prop,switch in [('WarningsAsErrors','/warnaserror+:'),('WarningsNotAsErrors','/warnaserror-:')]:
        codes=[]
        for warning in props[prop].replace(',',';').split(';'):
            warning=warning.strip()
            if not warning or warning.startswith('NU'):continue # NuGet restore diagnostics, not compiler warnings.
            if warning.startswith('CS'):warning=warning[2:]
            assert warning.isdigit() or re.fullmatch(r'[A-Z]+[0-9]+',warning),(prop,warning)
            codes.append(warning)
        if codes:args.append(switch+','.join(codes))
    warnings=[]
    for warning in props['NoWarn'].replace(',',';').split(';'):
        warning=warning.strip()
        if warning.startswith('CS'):warning=warning[2:]
        if warning.isdigit():warnings.append(warning)
    if warnings:args.append('/nowarn:'+','.join(warnings))
    if props['TreatWarningsAsErrors'].lower()=='true':args.append('/warnaserror+')
    if props['CheckForOverflowUnderflow'].lower()=='true':args.append('/checked+')
    args+=['/reference:"'+native(p)+'"' for p in refs.values()]+['/reference:'+alias+'="'+native(p)+'"' for alias,p in aliases]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)],folder,host.parent)
    records.append(dict(assembly=name,original_target='net10.0',original_source_sha256=originals,original_resources=resource_inputs,original_project_edges=edges,aliased_references=[dict(alias=a,path=native(p),sha256=sha(p)) for a,p in aliases],actual_reference_sha256={native(p):sha(p) for p in refs.values()},assembly_version=assembly_version,file_version=file_version,package_version=package_version,original_nullable=props['Nullable'],original_EnableAnalyzers=props['EnableAnalyzers'],original_EnablePublicApiAnalyzer=props.get('EnablePublicApiAnalyzer',''),original_EnableNETAnalyzers=props.get('EnableNETAnalyzers',''),original_auto_generate_assembly_version=props['AutoGenerateAssemblyVersion'],key_policy=keyname,output_sha256={ext:sha(destination.with_suffix('.'+ext)) for ext in (['dll','pdb','xml'] if props['GenerateDocumentationFile'].lower()=='true' else ['dll','pdb'])},original_production_source_changes=0,actual_defines=defines,original_NoWarn=props['NoWarn'],original_TreatWarningsAsErrors=props['TreatWarningsAsErrors'],original_GenerateDocumentationFile=props['GenerateDocumentationFile'],original_WarningLevel=props['WarningLevel'],original_WarningsAsErrors=props['WarningsAsErrors'],original_WarningsNotAsErrors=props['WarningsNotAsErrors']))
    outputs[name]=destination;(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,len(originals),'original source inputs',assembly_version,file_version,flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,dependency_assets=assets,original_project_edges_preserved=True,original_arcade_resource_version_tasks_executed=True,original_project_warning_policy_preserved=True,original_task_helper_bootstrap_host='net8.0',build_id='20260213.113',build_id_origin='Explicit build ID matching the original SDK TemplateEngine10.0.200-preview.26113.113 dependency',formal_package_built=False,other_original_framework_profiles_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
