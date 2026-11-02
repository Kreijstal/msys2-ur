"""Build original MSBuild17.11 NET8 prerequisites for SDK10 Roslyn tasks.

Source SDK8 OOB implementation dependencies are explicit bootstrap inputs;
formal packages and exact dependency-resolution gates remain open.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,zipfile,shutil,xml.etree.ElementTree as E

plan,out=(Path(p).resolve() for p in sys.argv[1:3]);reuse=Path(sys.argv[3]).resolve() if len(sys.argv)>3 and sys.argv[3]!='-' else None;version_input=Path(sys.argv[4]).resolve() if len(sys.argv)>4 else None;file_version=version_input.read_text().strip() if version_input else '17.11.48.0';out.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']).resolve()
model=json.loads((plan/'evaluated.json').read_text());prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
native=lambda p:Path(p).resolve().as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
host8=prefix/'lib/dotnet/dotnet.exe';sdk=host8.parent/'sdk/8.0.131'
refs=sorted((prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll'));assert len(refs)==163
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1')
feed=prefix/'lib/dotnet/library-packs';source_feed=plan.parent/'msbuild1711-source-packages'
pins={'Microsoft.CodeAnalysis.Collections':'854de69d3c5f2a92e06757d48dc136e9fa7887814a999917dc689733ee2431a8'}
binary_versions={n:'8.0.0' for n in ['System.Configuration.ConfigurationManager','System.Reflection.MetadataLoadContext','System.Resources.Extensions','System.CodeDom','System.Security.Cryptography.Pkcs','System.Security.Cryptography.Xml']}
key=bytes.fromhex(re.findall('PublicKey=([0-9a-f]+)',(source/'src/StringTools/AssemblyInfo.cs').read_text(encoding='utf-8-sig'))[-1]);assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
(out/'Microsoft.public.snk').write_bytes(key)
project_paths={}
for name,p in json.loads((plan/'wrappers.json').read_text()).items():
    entry=model[name];assert entry['properties']['TargetFramework']=='net8.0'
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
            package=source_feed/(dep.lower()+'.4.2.0-1.22102.8.nupkg');assert sha(package)==pins[dep]
            with zipfile.ZipFile(package) as z:
                for member in z.namelist():
                    if member.endswith('/'):continue
                    data=z.read(member);assert not data.startswith(b'MZ') and not member.lower().endswith(('.dll','.exe','.so','.dylib')),member
                target='netcoreapp3.1'
                selected=[n for n in z.namelist() if n.startswith('contentFiles/cs/'+target+'/') and n.endswith('.cs')]
                assert selected,dep
                for member in selected:
                    path=folder/'source-packages'/dep/member;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(member));files.append(path)
                    package_sources[dep+'/'+member]=sha(path)
            package_inputs[dep]=dict(version='4.2.0-1.22102.8',archive_sha256=sha(package),selected_source_profile=target,selected_source_files=len(selected))
        else:
            framework=next((p for p in refs if p.name==dep+'.dll'),None)
            path=framework or sdk/(dep+'.dll');assert path.is_file(),path
            references.append(path);package_inputs[dep]=dict(declared_minimum_version=binary_versions.get(dep,'8.0.0'),source_sdk8_bootstrap_path=native(path),compile_dll_sha256=sha(path),inbox_framework_reference_used=framework is not None,formal_exact_dependency_package_resolved=False)
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
    if package_sources:
        resx=folder/'Collections.Strings.resx'
        with zipfile.ZipFile(source_feed/'microsoft.codeanalysis.collections.4.2.0-1.22102.8.nupkg') as z:resx.write_bytes(z.read('contentFiles/cs/netcoreapp3.1/Internal/Strings.resx'))
        root=E.parse(resx);sr=folder/'Collections.SR.g.cs'
        sr.write_text('namespace Microsoft.CodeAnalysis.Collections { internal static class SR { private static readonly System.Resources.ResourceManager rm = new System.Resources.ResourceManager("Microsoft.CodeAnalysis.Collections.Strings", typeof(SR).Assembly);\n'+''.join('internal static string '+n.get('name')+' => rm.GetString('+json.dumps(n.get('name'))+')!;\n' for n in root.iter('data'))+'}}\n')
        files.append(sr)
        rp2=E.Element('Project');E.SubElement(rp2,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(sdk/'Microsoft.Build.Tasks.Core.dll'));t2=E.SubElement(rp2,'Target',Name='Resources');binary=folder/'Collections.Strings.resources';E.SubElement(t2,'GenerateResource',Sources=native(resx),OutputResources=native(binary),ExecuteAsTool='false');E.ElementTree(rp2).write(folder/'Collections.proj',encoding='utf-8',xml_declaration=True)
        run(folder,'collections-resources',[host8,'msbuild',folder/'Collections.proj','-t:Resources','-nologo','-v:minimal']);resources.append((binary,'Microsoft.CodeAnalysis.Collections.Strings.resources'))
    version='1.0.0.0' if name=='Microsoft.NET.StringTools' else '15.1.0.0'
    info=folder/'AssemblyInfo.g.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("'+version+'")]\n[assembly:System.Reflection.AssemblyFileVersion("'+file_version+'")]\n[assembly:System.Reflection.AssemblyInformationalVersion("17.11.48+02bf66295b64ab368d12933041f7281aad186a2d")]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v8.0")]\n');files.append(info)
    output=folder/(name+'.dll');defines=list(dict.fromkeys([v for v in entry['properties']['DefineConstants'].split(';') if v]+['NET'+str(i)+'_0_OR_GREATER' for i in range(5,9)]+['NETCOREAPP'+v+'_OR_GREATER' for v in ['1_0','1_1','2_0','2_1','2_2','3_0','3_1']]));assert 'DEBUG' not in defines
    generated=folder/'generated';generated.mkdir();regex=prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/analyzers/dotnet/cs/System.Text.RegularExpressions.Generator.dll'
    args=['/analyzer:"'+native(regex)+'"','/generatedfilesout:"'+native(generated)+'"','/nostdlib+','/target:'+('exe' if name=='MSBuild' else 'library'),'/langversion:preview','/nullable:enable','/unsafe+','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Microsoft.public.snk')+'"','/out:"'+native(output)+'"','/define:'+';'.join(defines)]
    args+=['/reference:"'+native(p)+'"' for p in references]+['/resource:"'+native(p)+'",'+logical for p,logical in resources]+['"'+native(p)+'"' for p in files]
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
    run(folder,'compile',[host,compiler,'-noconfig','@'+native(rsp)])
    record=dict(project=name,commands=commands,regex_generator_sha256=sha(regex),generated_regex_source_sha256={p.relative_to(folder).as_posix():sha(p) for p in generated.rglob('*.cs')},original_source_sha256=originals,original_resource_sha256=resource_inputs,source_package_inputs=package_inputs,source_package_cs_sha256=package_sources,project_dependencies=project_dependencies,actual_reference_sha256={native(p):sha(p) for p in references},output_sha256=sha(output),original_target='net8.0',original_production_source_changes=0,file_version=file_version,bootstrap_file_version='17.11.48.0' if version_input is None else None,original_arcade_version_policy_verified=version_input is not None,native_win32_resource_and_satellites_built=False,formal_package_built=False,full_msbuild_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
    (folder/'results.json').write_text(json.dumps(record,indent=2)+'\n');outputs[name]=output;results.append(record)
    (out/'progress.json').write_text(json.dumps(dict(completed_projects=list(outputs),full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',name,'original sources',len(originals),'source-package files',len(package_sources),flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=results,all6_project_compilations_passed=True,original_arcade_version_policy_verified=version_input is not None,native_resources_and_satellites_complete=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
