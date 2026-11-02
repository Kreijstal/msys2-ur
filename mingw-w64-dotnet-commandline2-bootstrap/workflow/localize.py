"""Build all original CommandLine2 satellite cultures for both original target frameworks."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
plan,build,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';p=E.Element('Project');E.SubElement(p,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));t=E.SubElement(p,'Target',Name='Generate');resx=source/'src/System.CommandLine/Properties/Resources.resx';ns={'x':'urn:oasis:names:tc:xliff:document:1.2'};expected=[];inputs={};commands=[]
for xlf in sorted((resx.parent/'xlf').glob('Resources.*.xlf')):
 tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');inputs[xlf.relative_to(source).as_posix()]=sha(xlf);values={n.get('id'):''.join(n.find('x:target',ns).itertext()) for n in tree.findall('.//x:trans-unit',ns) if n.find('x:target',ns) is not None};localized=E.parse(resx);strings={}
 for n in localized.iter('data'):
  v=n.find('value')
  if n.get('name') in values:v.text=values[n.get('name')]
  strings[n.get('name')]=(v.text or '').replace('\n',os.linesep)
 folder=out/culture;folder.mkdir();file=folder/'Resources.resx';localized.write(file,encoding='utf-8',xml_declaration=True);E.SubElement(t,'GenerateResource',Sources=native(file),OutputResources=native(file.with_suffix('.resources')),ExecuteAsTool='false');expected.append(dict(culture=culture,strings=strings))
assert len(expected)==14;E.ElementTree(p).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
def run(label,cmd,root):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(root),DOTNET_ROOT_X64=native(root)),timeout=180)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('resources',[host8,'msbuild',out/'Resources.proj','-t:Generate','-nologo','-v:minimal'],host8.parent);key=out/'public.snk';key.write_bytes(bytes.fromhex((here/'MicrosoftShared.pubkey.hex').read_text()));records=json.loads((build/'results.json').read_text())['projects'];jobs=[]
for record in records:
 tfm=record['original_target'];refs=sorted((prefix/('lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0' if tfm=='net10.0' else 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0')).glob('*.dll'));assert len(refs)==(167 if tfm=='net10.0' else 113)
 for item in expected:
  culture=item['culture'];folder=out/tfm/culture;folder.mkdir(parents=True);info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion('+json.dumps(record['assembly_version'])+')]\n[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(record['file_version'])+')]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n');dest=build/tfm/'bin'/culture/'System.CommandLine.resources.dll';dest.parent.mkdir();rsp=folder/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:library','/publicsign+','/deterministic+','/keyfile:"'+native(key)+'"','/out:"'+native(dest)+'"','/resource:"'+native(out/culture/'Resources.resources')+'",System.CommandLine.Properties.Resources.'+culture+'.resources']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(info)+'"'])+'\n');jobs.append((tfm+'-'+culture,[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)],dest))
def compile(job):
 label,cmd,dest=job;run(label,cmd,host.parent);return dest
satellites={}
with ThreadPoolExecutor(max_workers=2) as pool:
 for dest in pool.map(compile,jobs):satellites[dest.relative_to(build).as_posix()]=sha(dest)
assert len(satellites)==28;(out/'expected.json').write_text(json.dumps(expected,ensure_ascii=False)+'\n');(out/'results.json').write_text(json.dumps(dict(commands=commands,original_xlf_sha256=inputs,satellite_sha256=satellites,cultures=14,localized_values_per_framework=sum(len(i['strings']) for i in expected),full_dependency_goal_complete=False),indent=2)+'\n');print('PASS28 original NET10/NS2 satellite assemblies;all14 original cultures')
