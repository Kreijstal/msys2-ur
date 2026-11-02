"""Build all original NET10 NuGet foundation inputs from their evaluated projects."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

plan,out=(Path(p).resolve() for p in sys.argv[1:3]);reuse=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else None;out.mkdir();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);model=json.loads((plan/'evaluated.json').read_text());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));records=[];outputs={};commands=[]
binary=out/'bin';binary.mkdir()
def run(folder,label,command,environment=env):
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
for name in ['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel']:
    entry=model[name];props=entry['properties'];assert props['TargetFramework']==props['TargetFrameworks']=='net10.0';assert props['Version']=='7.3.0-preview.1.11413';assert props['AssemblyVersion']=='7.3.0.0' and props['FileVersion']=='7.3.0.11413'
    folder=out/name
    if reuse is not None:
        prior=next((r for r in json.loads((reuse/'progress.json').read_text()) if r['assembly']==name),None)
        if prior is not None:
            import shutil
            for rel,digest in prior['original_source_sha256'].items():assert sha(source/rel)==digest
            for path,digest in prior['actual_reference_sha256'].items():assert sha(Path(path))==digest
            assert sha(reuse/'bin'/(name+'.dll'))==prior['output_sha256']
            shutil.copytree(reuse/name,folder)
            for ext in ['dll','pdb']:shutil.copyfile(reuse/'bin'/(name+'.'+ext),binary/(name+'.'+ext))
            outputs[name]=binary/(name+'.dll');records.append(prior);print('REUSE verified unchanged successful project',name,flush=True);continue
    folder.mkdir();files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']));assert all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files};references=list(refs)
    for item in entry['items']['ProjectReference']:
        dep=Path(item['full_path']).stem;assert dep in outputs,dep;references.append(outputs[dep])
        for path,digest in next(r for r in records if r['assembly']==dep)['actual_reference_sha256'].items():assert sha(Path(path))==digest;references.append(Path(path))
    unique={}
    for ref in references:
        if ref.name in unique:assert sha(ref)==sha(unique[ref.name]),ref.name
        else:unique[ref.name]=ref
    references=list(unique.values())
    assert not entry['items']['PackageReference'],entry['items']['PackageReference']
    p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(p,'Target',Name='Generate');resources=[];resource_inputs={}
    project_folder=source/'src/NuGet.Core'/name
    for item in entry['items']['EmbeddedResource']:
        resx=Path(item['full_path']).resolve();assert resx.suffix=='.resx';resource_inputs[resx.relative_to(source).as_posix()]=sha(resx)
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
    destination=binary/(name+'.dll');args=['/nostdlib+','/target:library','/langversion:preview','/nullable:enable','/optimize+','/unsafe+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(Path(props['AssemblyOriginatorKeyFile']))+'"','/out:"'+native(destination)+'"','/doc:"'+native(destination.with_suffix('.xml'))+'"','/define:'+';'.join(defines)]
    args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(folder,name+'-compile',[host,compiler,'-noconfig','@'+native(rsp)])
    records.append(dict(assembly=name,original_target='net10.0',original_source_sha256=originals,original_resource_sha256=resource_inputs,actual_reference_sha256={native(p):sha(p) for p in references},output_sha256=sha(destination),original_version=props['Version'],assembly_version=props['AssemblyVersion'],file_version=props['FileVersion'],original_production_source_changes=0))
    outputs[name]=destination;(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',name,len(originals),'unchanged original source inputs',flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,original_vmr_net10_profile=True,formal_package_built=False,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
