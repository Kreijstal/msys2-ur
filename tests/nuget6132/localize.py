"""Build all original Extensions10 XLF resources grouped into satellites."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);records=json.loads((build/'results.json').read_text())['projects'];native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for r in records:
 r['original_framework']=r['original_target']
 base=Path('src/NuGet.Core')/r['assembly']
 r['original_resources']={rel:dict(logical_name=r['assembly']+'.'+Path(rel).relative_to(base).with_suffix('').as_posix().replace('/','.')) for rel in r['original_resource_sha256'] if rel.endswith('.resx')}
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(p,'Target',Name='Generate');ns={'x':'urn:oasis:names:tc:xliff:document:1.2'};expected=[];inputs={};groups={};commands=[]
for record in records:
    name=record['assembly']
    for rel,meta in record['original_resources'].items():
        resx=source/rel
        for xlf in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
            tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');values={n.get('id'):''.join(n.find('x:target',ns).itertext()) for n in tree.findall('.//x:trans-unit',ns) if n.find('x:target',ns) is not None};inputs[xlf.relative_to(source).as_posix()]=sha(xlf)
            localized=E.parse(resx);strings={}
            for n in localized.iter('data'):
                v=n.find('value')
                if n.get('name') in values:v.text=values[n.get('name')]
                strings[n.get('name')]=(v.text or '').replace('\n',os.linesep)
            logical=meta['logical_name'];folder=out/name/culture;folder.mkdir(parents=True,exist_ok=True);file=folder/(logical+'.resx');localized.write(file,encoding='utf-8',xml_declaration=True);E.SubElement(target,'GenerateResource',Sources=native(file),OutputResources=native(file.with_suffix('.resources')),ExecuteAsTool='false')
            groups.setdefault((name,culture),dict(record=record,folder=folder,resources=[]))['resources'].append((file.with_suffix('.resources'),logical+'.'+culture+'.resources'))
            expected.append(dict(assembly=name,culture=culture,resource=logical,strings=strings))
E.ElementTree(p).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
def run(label,cmd,root):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(root),DOTNET_ROOT_X64=native(root)),timeout=180)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('resources',[host8,'msbuild',out/'Resources.proj','-t:Generate','-nologo','-v:minimal'],host8.parent)
def compile_satellite(item):
    (name,culture),g=item;folder=g['folder'];record=g['record'];key=folder/'public.snk';key.write_bytes((source/'keys/35MSSharedLib1024.snk').read_bytes());info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion('+json.dumps(record['assembly_version'])+')]\n[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(record['file_version'])+')]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n');dest=build/'bin'/culture/(name+'.resources.dll');dest.parent.mkdir(exist_ok=True)
    args=['/nostdlib+','/target:library','/deterministic+','/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(dest)+'"']+['/resource:"'+native(p)+'",'+logical for p,logical in g['resources']]+['/reference:"'+native(p)+'"' for p in (refs if record['original_framework']=='net10.0' else sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll')))]+['"'+native(info)+'"'];rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');run(name+'-'+culture,[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)],host.parent);return dest
satellites={}
with ThreadPoolExecutor(max_workers=2) as pool:
    for dest in pool.map(compile_satellite,groups.items()):satellites[dest.relative_to(build/'bin').as_posix()]=sha(dest)
assert len(satellites)==len(groups) and len(expected)==len(inputs),(len(satellites),len(groups),len(expected),len(inputs))
(out/'expected.json').write_text(json.dumps(expected,ensure_ascii=False)+'\n');(out/'results.json').write_text(json.dumps(dict(commands=commands,original_xlf_sha256=inputs,satellite_sha256=satellites,localized_resource_sets=len(expected),localized_values=sum(len(p['strings']) for p in expected),full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(satellites),'original NuGet6.13.2 satellites and',len(expected),'localized resource sets')
