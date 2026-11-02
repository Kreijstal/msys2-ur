"""Compile all six original NET10 MSBuild projects against audited source assets."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,zipfile,shutil,xml.etree.ElementTree as E

plan,out=(Path(p).resolve() for p in sys.argv[1:3]);reuse=Path(sys.argv[3]).resolve() if len(sys.argv)>3 and sys.argv[3]!='-' else None;version_input=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None;file_version=version_input.read_text().strip() if version_input else '18.3.0.0';out.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']).resolve()
model=json.loads((plan/'evaluated.json').read_text());prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
native=lambda p:Path(p).resolve().as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
host8=prefix/'lib/dotnet/dotnet.exe';sdk=host8.parent/'sdk/8.0.131'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
feed=prefix/'lib/dotnet/library-packs';source_feed=plan.parent/'msbuild-source-packages'
pins={'Microsoft.CodeAnalysis.Contracts':'7613b5ba957ba01667db49d98d89363315eaf14114213bab185012d3424c0b10','Microsoft.CodeAnalysis.Collections':'7956c4437110b99eb70887c1ed3dbb5c08c062b8b9f5f4079dccfdd638cd47fd','Microsoft.CodeAnalysis.PooledObjects':'b872225038cf0810f0c184f9204c2e4bc8a57ccd0f1265ca0b98efafdd9f3334'}
binary_versions={'Microsoft.VisualStudio.SolutionPersistence':'1.0.52','System.Configuration.ConfigurationManager':'9.0.11','System.Reflection.MetadataLoadContext':'9.0.11','System.Resources.Extensions':'9.0.11','System.CodeDom':'9.0.11','System.Security.Cryptography.Pkcs':'9.0.11','System.Security.Cryptography.Xml':'9.0.11'}
key=bytes.fromhex(re.findall('PublicKey=([0-9a-f]+)',(source/'src/StringTools/AssemblyInfo.cs').read_text(encoding='utf-8-sig'))[-1]);assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
(out/'Microsoft.public.snk').write_bytes(key)
project_paths={}
for name,p in json.loads((plan/'wrappers.json').read_text()).items():
    entry=model[name];assert entry['properties']['TargetFramework']=='net10.0'
    path=Path(p).name
    project_paths[Path(path).stem]=name
project_paths['StringTools']='Microsoft.NET.StringTools';project_paths['Microsoft.Build.Utilities']='Microsoft.Build.Utilities.Core';project_paths['Microsoft.Build.Tasks']='Microsoft.Build.Tasks.Core'
outputs={};results=[]
def run(folder,label,command):
    with (folder/(label+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=result.returncode))
    assert result.returncode==0,(name,label,result.returncode,str(folder/(label+'.log')))
for name in ['Microsoft.NET.StringTools','Microsoft.Build.Framework','Microsoft.Build','Microsoft.Build.Utilities.Core','Microsoft.Build.Tasks.Core','MSBuild']:
    folder=out/name;entry=model[name];commands=[]
    if reuse is not None and (reuse/name/'results.json').is_file():
        old=json.loads((reuse/name/'results.json').read_text());assert old.get('file_version',old.get('bootstrap_file_version'))==file_version
        assert 'NETCOREAPP2_1_OR_GREATER' in (reuse/name/'compile.rsp').read_text()
        for relative,digest in old['original_source_sha256'].items():assert sha(source/relative)==digest
        for path,digest in old['actual_reference_sha256'].items():assert sha(Path(path))==digest
        assert sha(reuse/name/(name+'.dll'))==old['output_sha256']
        shutil.copytree(reuse/name,folder);outputs[name]=folder/(name+'.dll');results.append(old)
        print('REUSE verified terminal-success unchanged project',name,flush=True);continue
    folder.mkdir()
    files=list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']))
    assert files and all(p.is_file() and p.is_relative_to(source) for p in files)
    originals={p.relative_to(source).as_posix():sha(p) for p in files}
    references=list(refs);project_dependencies={};package_inputs={};package_sources={}
    for item in entry['items']['ProjectReference']:
        dep=project_paths[Path(item['full_path']).stem];assert dep in outputs,dep
        if outputs[dep] not in references:references.append(outputs[dep])
        project_dependencies[dep]=sha(outputs[dep])
    for item in entry['items']['PackageReference']:
        dep=item['identity']
        if dep in pins:
            package=source_feed/(dep.lower()+'.5.0.0-1.25277.114.nupkg');assert sha(package)==pins[dep]
            with zipfile.ZipFile(package) as z:
                for member in z.namelist():
                    if member.endswith('/'):continue
                    data=z.read(member);assert not data.startswith(b'MZ') and not member.lower().endswith(('.dll','.exe','.so','.dylib')),member
                target='netstandard2.0' if dep=='Microsoft.CodeAnalysis.PooledObjects' else 'net9.0'
                selected=[n for n in z.namelist() if n.startswith('contentFiles/cs/'+target+'/') and n.endswith('.cs')]
                assert selected,dep
                for member in selected:
                    path=folder/'source-packages'/dep/member;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(member));files.append(path)
                    package_sources[dep+'/'+member]=sha(path)
            package_inputs[dep]=dict(version='5.0.0-1.25277.114',archive_sha256=sha(package),selected_source_profile=target,selected_source_files=len(selected))
        else:
            version=binary_versions[dep];package=feed/(dep.lower()+'.'+version+'.nupkg')
            with zipfile.ZipFile(package) as z:
                target='net8.0' if dep=='Microsoft.VisualStudio.SolutionPersistence' else 'net9.0'
                member='lib/'+target+'/'+dep+'.dll';path=folder/'dependencies'/(dep+'.dll');path.parent.mkdir(exist_ok=True);path.write_bytes(z.read(member))
            references.append(path);package_inputs[dep]=dict(version=version,source_archive_sha256=sha(package),compile_member=member,compile_dll_sha256=sha(path))
    # Resolve transitive project/package references just as SDK reference resolution does.
    for dep in project_dependencies:
        dep_record=next(r for r in results if r['project']==dep)
        for path,digest in dep_record['actual_reference_sha256'].items():
            p=Path(path);assert sha(p)==digest;references.append(p)
    unique={}
    for p in references:
        key_name=p.name.lower()
        if key_name in unique:assert sha(unique[key_name])==sha(p),(name,key_name)
        else:unique[key_name]=p
    references=list(unique.values())
    resources=[];resource_inputs={};rp=E.Element('Project');E.SubElement(rp,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(sdk/'Microsoft.Build.Tasks.Core.dll'));rt=E.SubElement(rp,'Target',Name='Resources')
    for index,item in enumerate(entry['items']['EmbeddedResource']):
        path=Path(item['full_path']).resolve();assert path.is_file() and path.is_relative_to(source),path
        metadata=item['metadata'];logical=metadata.get('LogicalName') or entry['properties']['RootNamespace']+'.Resources.'+path.name;resource_inputs[path.relative_to(source).as_posix()]=sha(path)
        if path.suffix in {'.resx','.txt'}:
            binary=folder/('resource-'+str(index)+'.resources');E.SubElement(rt,'GenerateResource',Sources=native(path),OutputResources=native(binary),ExecuteAsTool='false');resources.append((binary,logical))
        else:resources.append((path,logical))
    if len(rt):
        E.ElementTree(rp).write(folder/'Resources.proj',encoding='utf-8',xml_declaration=True)
        run(folder,'resources',[host8,'msbuild',folder/'Resources.proj','-t:Resources','-nologo','-v:minimal'])
    version='1.0.0.0' if name=='Microsoft.NET.StringTools' else '15.1.0.0'
    info=folder/'AssemblyInfo.g.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("'+version+'")]\n[assembly:System.Reflection.AssemblyFileVersion("'+file_version+'")]\n[assembly:System.Reflection.AssemblyInformationalVersion("18.3.0-release-26113-113+228caa11ad0046ccb599530abd9aba4e1979b5e9")]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]\n');files.append(info)
    output=folder/(name+'.dll');defines=list(dict.fromkeys([v for v in entry['properties']['DefineConstants'].split(';') if v]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,11)]+['NETCOREAPP'+v+'_OR_GREATER' for v in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]));assert 'DEBUG' not in defines
    generated=folder/'generated';generated.mkdir();regex=prefix/'lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs/System.Text.RegularExpressions.Generator.dll'
    args=['/analyzer:"'+native(regex)+'"','/generatedfilesout:"'+native(generated)+'"','/nostdlib+','/target:'+('exe' if name=='MSBuild' else 'library'),'/langversion:preview','/nullable:enable','/unsafe+','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Microsoft.public.snk')+'"','/out:"'+native(output)+'"','/define:'+';'.join(defines)]
    args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
    run(folder,'compile',[host,compiler,'-noconfig','@'+native(rsp)])
    record=dict(project=name,commands=commands,regex_generator_sha256=sha(regex),generated_regex_source_sha256={p.relative_to(folder).as_posix():sha(p) for p in generated.rglob('*.cs')},original_source_sha256=originals,original_resource_sha256=resource_inputs,source_package_inputs=package_inputs,source_package_cs_sha256=package_sources,project_dependencies=project_dependencies,actual_reference_sha256={native(p):sha(p) for p in references},output_sha256=sha(output),original_target='net10.0',original_production_source_changes=0,file_version=file_version,bootstrap_file_version='18.3.0.0' if version_input is None else None,original_arcade_version_policy_verified=version_input is not None,native_win32_resource_and_satellites_built=False,formal_package_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
    (folder/'results.json').write_text(json.dumps(record,indent=2)+'\n');outputs[name]=output;results.append(record)
    (out/'progress.json').write_text(json.dumps(dict(completed_projects=list(outputs),full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',name,'original sources',len(originals),'source-package files',len(package_sources),flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=results,all6_project_compilations_passed=True,original_arcade_version_policy_verified=version_input is not None,native_resources_and_satellites_complete=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
