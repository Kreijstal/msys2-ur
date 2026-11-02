"""Strictly compare original VMR NET10 reference-source contracts with support outputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;source=plan/'snapshot/runtime';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[];records={}
def run(label,cmd):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=150)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));return r.returncode
for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(n+'.dll'),out/(n+'.dll'))
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Api.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[out/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']]]+['"'+native(here/'CompareApi.cs')+'"']
(out/'tool.rsp').write_text('\n'.join(args)+'\n');assert run('tool',[host,compiler/'csc.dll','-noconfig','@'+native(out/'tool.rsp')])==0
(out/'Api.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
for name,keyname in [('Microsoft.Extensions.DependencyInjection.Abstractions','MicrosoftAspNetCore'),('Microsoft.Extensions.Logging.Abstractions','MicrosoftAspNetCore')]:
    folder=out/name;folder.mkdir();project=source/'src/libraries'/name/'ref'/(name+'.csproj');files=[]
    for group in E.parse(project).getroot().findall('ItemGroup'):
        if not group.findall('Compile'):continue
        condition=group.get('Condition')
        if condition:
            assert condition=="'$(TargetFrameworkIdentifier)' != '.NETCoreApp'"
            continue
        for item in group.findall('Compile'):
            condition=item.get('Condition')
            if condition:assert condition=="'$(TargetFrameworkIdentifier)' == '.NETCoreApp'"
            value=item.get('Include');assert '$(' not in value
            files.append(project.parent/value)
    key=folder/'public.snk';key.write_bytes(bytes.fromhex((here/(keyname+'.pubkey.hex')).read_text()));info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("10.0.0.0")]\n')
    project_refs=refs+([out/'Microsoft.Extensions.DependencyInjection.Abstractions/Microsoft.Extensions.DependencyInjection.Abstractions.dll'] if name.endswith('Logging.Abstractions') else [])
    contract=folder/(name+'.dll');args=['/nostdlib+','/target:library','/nullable:enable','/refonly','/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(contract)+'"']+['/reference:"'+native(p)+'"' for p in project_refs]+['"'+native(p)+'"' for p in files+[info]]
    (folder/'contract.rsp').write_text('\n'.join(args)+'\n');assert run(name+'-contract',[host,compiler/'csc.dll','-noconfig','@'+native(folder/'contract.rsp')])==0
    reference_dir=folder/'refs';reference_dir.mkdir()
    for ref in project_refs:shutil.copyfile(ref,reference_dir/ref.name)
    rc=run(name+'-compare',[host,out/'Api.dll',contract,build/'bin'/(name+'.dll'),reference_dir,folder/'api-results.json']);record=json.loads((folder/'api-results.json').read_text());records[name]=dict(original_contract_source_sha256={p.relative_to(source).as_posix():sha(p) for p in files},comparison=record,exit_code=rc)
    print(name,'entries',record['expected_entries'],'differences',record['total_differences'],'nullable differences',len(record['nullable_annotation_differences']),flush=True)
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,full_dependency_goal_complete=False),indent=2)+'\n');assert all(p['exit_code']==0 for p in records.values())
