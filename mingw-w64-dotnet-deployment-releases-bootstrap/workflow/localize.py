"""Build original Releases NS2 XLF satellites."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
from concurrent.futures import ThreadPoolExecutor

root=Path(sys.argv[1]).resolve();build=root/'build';out=root/'localized';out.mkdir();source=root/'source/src/deployment-tools';prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==113
here=Path(__file__).resolve().parent;key=out/'public.snk';key.write_bytes(bytes.fromhex((here/'MicrosoftShared.pubkey.hex').read_text()));project=E.Element('Project');E.SubElement(project,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(project,'Target',Name='Generate');ns={'x':'urn:oasis:names:tc:xliff:document:1.2'};expected=[];inputs={};commands=[]
for name in ['Microsoft.Deployment.DotNet.Releases']:
    for resx in (source/'src'/name/'src').glob('*.resx'):
        for xlf in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
            tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');inputs[xlf.relative_to(source).as_posix()]=sha(xlf);values={n.get('id'):''.join(n.find('x:target',ns).itertext()) for n in tree.findall('.//x:trans-unit',ns) if n.find('x:target',ns) is not None}
            localized=E.parse(resx);strings={}
            for n in localized.iter('data'):
                value=n.find('value')
                if n.get('name') in values:value.text=values[n.get('name')]
                strings[n.get('name')]=(value.text or '').replace('\n',os.linesep)
            folder=out/name/culture;folder.mkdir(parents=True);resource=folder/(name+'.'+resx.stem+'.resx');localized.write(resource,encoding='utf-8',xml_declaration=True);E.SubElement(target,'GenerateResource',Sources=native(resource),OutputResources=native(resource.with_suffix('.resources')),ExecuteAsTool='false')
            expected.append(dict(assembly=name,resource=name+'.'+resx.stem,culture=culture,strings=strings))
E.ElementTree(project).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
def run(label,command,env):
    with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('resources',[host8,'msbuild',out/'Resources.proj','-t:Generate','-nologo'],dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent)))
satellites={};jobs=[]
for item in expected:
    name=item['assembly'];culture=item['culture'];folder=out/name/culture;info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("2.0.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("2.0.25.61305")]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n')
    resource=folder/(item['resource']+'.resources');destination=build/culture/(name+'.resources.dll');destination.parent.mkdir(exist_ok=True)
    args=['/nostdlib+','/target:library','/deterministic+','/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(destination)+'"','/resource:"'+native(resource)+'",'+item['resource']+'.'+culture+'.resources']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(info)+'"']
    rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');jobs.append((name+'-'+culture,[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)],dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent)),destination))
def compile_satellite(job):
    label,command,env,destination=job;run(label,command,env);return destination
with ThreadPoolExecutor(max_workers=2) as pool:
    for destination in pool.map(compile_satellite,jobs):satellites[destination.relative_to(build).as_posix()]=sha(destination)
assert len(satellites)==13
(out/'expected.json').write_text(json.dumps(expected,ensure_ascii=False)+'\n');(out/'results.json').write_text(json.dumps(dict(commands=commands,original_xlf_sha256=inputs,satellite_sha256=satellites,localized_resource_sets=len(expected),localized_values=sum(len(i['strings']) for i in expected),full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(satellites),'original Releases NS2 satellites')
