"""Build the original NuGet6.13.2 NET10 closure using actual restored source dependencies."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as E

plan,dependency_restore,out=(Path(p).resolve() for p in sys.argv[1:4]);reuse=None;out.mkdir();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);model=json.loads((plan/'evaluated.json').read_text());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));records=[];outputs={};commands=[]
binary=out/'bin';binary.mkdir()
def run(folder,label,command,environment=env):
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
feed=prefix/'lib/dotnet/library-packs';dependency_records=[];transitive={}
def package_asset(package,version,member,destination):
    archive=next(p for p in feed.iterdir() if p.name.lower()==f'{package}.{version}.nupkg'.lower())
    with zipfile.ZipFile(archive) as z:destination.write_bytes(z.read(member))
    dependency_records.append(dict(package=package,version=version,archive=native(archive),archive_sha256=sha(archive),member=member,output=native(destination),output_sha256=sha(destination)))
    return destination
external={}
restored=json.loads((dependency_restore/'results.json').read_text())
for name,record in restored['actual_source_packages'].items():
 members=[m for m in record['compile_assets'] if m.endswith('.dll')]
 if not members:continue
 assert len(members)==1,(name,members)
 external[name]=package_asset(name,record['version'],members[0],binary/Path(members[0]).name)
names=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.Configuration','NuGet.Packaging','NuGet.Protocol','NuGet.Credentials']
for name in names:
    entry=model[name];props=entry['properties'];assert props['TargetFramework']=='net10.0' and 'net10.0' in props['TargetFrameworks'].split(';');assert props['Version']=='6.13.2';assert props['AssemblyVersion']=='6.13.2.1' and props['FileVersion']=='6.13.2.1'
    folder=out/name
    folder.mkdir();files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']));assert all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files};references=list(refs)
    for item in entry['items']['ProjectReference']:
        dep=Path(item['full_path']).stem;assert dep in outputs,dep;references.append(outputs[dep])
        references.extend(transitive[dep])
    for item in entry['items']['PackageReference']:
        dep=item['identity'];assert dep in external,dep;references.append(external[dep])
        if dep=='Microsoft.Extensions.FileProviders.Abstractions':references.append(external['Microsoft.Extensions.Primitives'])
    transitive[name]=references[len(refs):]
    unique={}
    for ref in references:
        if ref.name in unique and ref not in external.values():assert sha(ref)==sha(unique[ref.name]),ref.name
        unique[ref.name]=ref
    references=list(unique.values())
    if reuse is not None:
        prior=next((r for r in json.loads((reuse/'progress.json').read_text()) if r['assembly']==name),None)
        if prior is not None:
            assert originals==prior['original_source_sha256']
            assert {p.name:sha(p) for p in references}=={Path(p).name:h for p,h in prior['actual_reference_sha256'].items()}
            assert sha(reuse/'bin'/(name+'.dll'))==prior['output_sha256']
            shutil.copytree(reuse/name,folder,dirs_exist_ok=True)
            for ext in ['dll','pdb']:shutil.copyfile(reuse/'bin'/(name+'.'+ext),binary/(name+'.'+ext))
            outputs[name]=binary/(name+'.dll');records.append(prior);print('REUSE verified unchanged successful project',name,flush=True);continue
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
    attrs=['[assembly:System.Reflection.AssemblyVersion("6.13.2.1")]','[assembly:System.Reflection.AssemblyFileVersion("6.13.2.1")]','[assembly:System.Reflection.AssemblyInformationalVersion('+json.dumps(props['InformationalVersion'])+')]','[assembly:System.Resources.NeutralResourcesLanguage("en-US")]','[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]']
    for item in entry['items']['InternalsVisibleTo']:
        key=item['metadata'].get('PublicKey');assert key
        attrs.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo('+json.dumps(item['identity']+', PublicKey='+key)+')]')
    info=folder/'AssemblyInfo.g.cs';info.write_text('\n'.join(attrs)+'\n');files.append(info)
    defines=list(dict.fromkeys(props['DefineConstants'].split(';')+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]+['NETCOREAPP'+s+'_OR_GREATER' for s in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]));assert 'DEBUG' not in defines and 'IS_CORECLR' in defines
    destination=binary/(name+'.dll');args=['/nostdlib+','/target:library','/langversion:preview','/nullable:'+(props['Nullable'] or 'disable'),'/optimize+','/unsafe+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(Path(props['AssemblyOriginatorKeyFile']))+'"','/out:"'+native(destination)+'"','/define:'+';'.join(defines)]
    if props['NoWarn']:args.append('/nowarn:'+props['NoWarn'].replace(';',','))
    if props['TreatWarningsAsErrors'].lower()=='true':args.append('/warnaserror+')
    if props['GenerateDocumentationFile'].lower()=='true':args.append('/doc:"'+native(destination.with_suffix('.xml'))+'"')
    args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
    generators=[]
    if any('JsonSerializerContext' in p.read_text(encoding='utf-8-sig') for p in files):
        generator=prefix/'lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs/System.Text.Json.SourceGeneration.dll'
        assert generator.is_file();generators.append(generator);args.append('/analyzer:"'+native(generator)+'"')
        generated=folder/'generated';generated.mkdir();args.append('/generatedfilesout:"'+native(generated)+'"')
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(folder,name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)])
    records.append(dict(assembly=name,original_target='net10.0',original_source_sha256=originals,original_resource_sha256=resource_inputs,actual_reference_sha256={native(p):sha(p) for p in references},source_generators_sha256={native(p):sha(p) for p in generators},output_sha256=sha(destination),original_version=props['Version'],assembly_version=props['AssemblyVersion'],file_version=props['FileVersion'],original_production_source_changes=0,declared_package_references=entry['items']['PackageReference']))
    outputs[name]=destination;(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,len(originals),'unchanged original source inputs',flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,dependency_assets=dependency_records,original_package_requirements=restored['original_requirements'],actual_source_dependency_restore=restored,original_source_only_NET10_profile=True,formal_package_built=False,TemplateEngine_NuGet6132_seven_project_closure_built=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
