"""Strictly compare original release NET8 reference-source contracts with support outputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;source=plan/'snapshot/runtime';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';toolrefs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(toolrefs)==167;refs=[p for p in (prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll') if p.name!='System.Collections.Immutable.dll'];assert len(refs)==162
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[];records={}
def run(label,cmd):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=150)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));return r.returncode
for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(n+'.dll'),out/(n+'.dll'))
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Api.dll')+'"']+['/reference:"'+native(p)+'"' for p in toolrefs+[out/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']]]+['"'+native(here/'CompareApi.cs')+'"']
(out/'tool.rsp').write_text('\n'.join(args)+'\n');assert run('tool',[host,compiler/'csc.dll','-noconfig','@'+native(out/'tool.rsp')])==0
(out/'Api.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
contracts=[]
for name,keyname in [('System.Collections.Immutable','Microsoft')]:
    folder=out/name;folder.mkdir();project=source/'src/libraries'/name/'ref'/(name+'.csproj');files=[]
    for group in E.parse(project).getroot().findall('ItemGroup'):
        if not group.findall('Compile'):continue
        condition=group.get('Condition')
        if condition:
            assert condition in ["'$(TargetFrameworkIdentifier)' != '.NETCoreApp'", "!$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net8.0'))"]
            continue
        for item in group.findall('Compile'):
            condition=item.get('Condition')
            if condition:assert condition=="'$(TargetFrameworkIdentifier)' == '.NETCoreApp'"
            value=item.get('Include');assert '$(' not in value
            files.append(project.parent/value)
    key=folder/'public.snk';key.write_bytes(bytes.fromhex((here/(keyname+'.pubkey.hex')).read_text()));info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("8.0.0.0")]\n')
    project_refs=refs+contracts
    contract=folder/(name+'.dll');args=['/nostdlib+','/target:library','/nullable:enable','/refonly','/define:NET;NETCOREAPP;NET8_0;'+ ';'.join('NET'+str(i)+'_0_OR_GREATER' for i in range(5,9)),'/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(contract)+'"']+['/reference:"'+native(p)+'"' for p in project_refs]+['"'+native(p)+'"' for p in files+[info]]
    (folder/'contract.rsp').write_text('\n'.join(args)+'\n');assert run(name+'-contract',[host,compiler/'csc.dll','-noconfig','@'+native(folder/'contract.rsp')])==0
    reference_dir=folder/'refs';reference_dir.mkdir()
    for ref in project_refs:shutil.copyfile(ref,reference_dir/ref.name)
    contracts.append(contract)
    rc=run(name+'-compare',[host,out/'Api.dll',contract,build/'bin'/(name+'.dll'),reference_dir,folder/'api-results.json']);record=json.loads((folder/'api-results.json').read_text());records[name]=dict(original_contract_source_sha256={p.relative_to(source).as_posix():sha(p) for p in files},comparison=record,exit_code=rc)
    print(name,'entries',record['expected_entries'],'differences',record['total_differences'],'nullable differences',len(record['nullable_annotation_differences']),flush=True)
# Regression: internal implementation interfaces are excluded; public interfaces remain mandatory.
fixtures=out/'visibility-fixtures';fixtures.mkdir();fixture_outputs={}
for variant,body in {'reference':'public interface IPublic {} public class Api : IPublic {}','implementation':'public interface IPublic {} internal interface IInternal {} public class Api : IPublic, IInternal {}','missing-public':'public interface IPublic {} public class Api {}'}.items():
 folder=fixtures/variant;folder.mkdir();file=folder/'Fixture.cs';file.write_text(body);target=folder/'Fixture.dll'
 arguments=['/nostdlib+','/target:library','/out:"'+native(target)+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(file)+'"'];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(arguments)+'\n');assert run('fixture-'+variant,[host,compiler/'csc.dll','-noconfig','@'+native(rsp)])==0;fixture_outputs[variant]=target
fixture_refs=out/'System.Collections.Immutable/refs'
assert run('fixture-internal-interface',[host,out/'Api.dll',fixture_outputs['reference'],fixture_outputs['implementation'],fixture_refs,fixtures/'internal-interface.json'])==0
assert run('fixture-public-interface-loss',[host,out/'Api.dll',fixture_outputs['reference'],fixture_outputs['missing-public'],fixture_refs,fixtures/'public-interface-loss.json'])==1
(out/'results.json').write_text(json.dumps(dict(projects=records,commands=commands,internal_interface_exclusion_and_negative_public_interface_loss_regressions_passed=True,full_dependency_goal_complete=False),indent=2)+'\n');assert all(p['exit_code']==0 for p in records.values())
