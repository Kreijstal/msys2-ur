"""Compile all original task XLF satellites with exact resource-value inventory."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();out=root/'localized';out.mkdir();source=root/'roslyn-source';resx=source/'src/Compilers/Core/MSBuildTask/ErrorString.resx'
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
project=E.Element('Project');E.SubElement(project,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));t=E.SubElement(project,'Target',Name='Generate');ns={'x':'urn:oasis:names:tc:xliff:document:1.2'};expected=[];inputs={};commands=[]
for xlf in sorted((resx.parent/'xlf').glob('ErrorString.*.xlf')):
    tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');inputs[xlf.relative_to(source).as_posix()]=sha(xlf)
    values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in tree.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
    localized=E.parse(resx);strings={}
    for node in localized.iter('data'):
        key=node.get('name');value=node.find('value')
        if key in values:value.text=values[key]
        strings[key]=(value.text or '').replace('\n',os.linesep)
    folder=out/culture;folder.mkdir();resource=folder/'Microsoft.CodeAnalysis.BuildTasks.ErrorString.resx';localized.write(resource,encoding='utf-8',xml_declaration=True)
    E.SubElement(t,'GenerateResource',Sources=native(resource),OutputResources=native(resource.with_suffix('.resources')),ExecuteAsTool='false')
    expected.append(dict(culture=culture,strings=strings))
E.ElementTree(project).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
def run(label,command,env):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('resources',[host8,'msbuild',out/'Resources.proj','-t:Generate','-nologo'],dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent)))
satellites={}
for item in expected:
    culture=item['culture'];folder=out/culture;info=folder/'AssemblyInfo.cs'
    info.write_text('[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n')
    destination=folder/'Microsoft.Build.Tasks.CodeAnalysis.resources.dll';resource=folder/'Microsoft.CodeAnalysis.BuildTasks.ErrorString.resources'
    args=['/nostdlib+','/target:library','/deterministic+','/publicsign+','/keyfile:"'+native(root/'task/Roslyn.public.snk')+'"','/out:"'+native(destination)+'"','/resource:"'+native(resource)+'",Microsoft.CodeAnalysis.BuildTasks.ErrorString.'+culture+'.resources']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(info)+'"']
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
    run('compile-'+culture,[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)],dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent)))
    satellites[destination.relative_to(out).as_posix()]=sha(destination)
assert len(satellites)==13
(out/'expected.json').write_text(json.dumps(expected,ensure_ascii=False)+'\n')
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_xlf_sha256=inputs,satellite_sha256=satellites,localized_resource_sets=len(expected),localized_values=sum(len(i['strings']) for i in expected),full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS all13 original Roslyn MSBuild task XLF satellites compiled')
