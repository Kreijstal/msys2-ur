"""Build NET10 compiler satellites from original RESX/XLF and run the API suite."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,shutil,subprocess,sys,xml.etree.ElementTree as E

prepared,build,out=(Path(p).resolve() for p in sys.argv[1:4])
assert not out.exists();out.mkdir();source=prepared/'roslyn-source'
here=Path(__file__).resolve().parent
@lru_cache(maxsize=None)
def native(p):
 value=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',value):return value[1].upper()+':'+value[2:]
 if value.startswith('/clang64/'):return native(Path('/clang64'))+value[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',value],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((build/'build-status.json').read_text());assert len(status)==3
binary=out/'bin';shutil.copytree(build/'bin',binary)
for name,r in status.items():assert sha(binary/(name+'.dll'))==r['output_sha256']
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
host='/clang64/lib/dotnet10/dotnet.exe';sdkhost='/clang64/lib/dotnet/dotnet.exe'
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable')
commands=[]
def run(label,command,environment=env):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
def compile(label,files,output,references,extras=()):
 args=['/nostdlib+','/target:library','/langversion:preview','/nullable:enable','/deterministic+','/debug:portable','/out:"'+native(output)+'"',*extras]
 args+=['/reference:"'+native(p)+'"' for p in references]+['"'+native(p)+'"' for p in files]
 rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n')
 run(label,[host,native(binary/'csc.dll'),'-noconfig','@'+native(rsp)])
resources=[];originals={};ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
project=E.Element('Project');target=E.SubElement(project,'Target',Name='Generate')
for name,language,suffix in [('Microsoft.CodeAnalysis','Core','common'),('Microsoft.CodeAnalysis.CSharp','CSharp','csharp')]:
 main=source/'src/Compilers'/language/'Portable'
 api=[]
 for filename in ['PublicAPI.Shipped.txt','PublicAPI.Unshipped.txt']:
  path=main/filename;originals[path.relative_to(source).as_posix()]=sha(path);api.append(path.read_text().rstrip())
 (out/('api-'+suffix+'.txt')).write_text('\n'.join(api)+'\n')
 for resx in main.glob('*.resx'):
  originals[resx.relative_to(source).as_posix()]=sha(resx)
  logical=name+'.'+resx.stem
  resources.append(dict(assembly=name,resource=logical,culture='',strings={i.get('name'):i.findtext('value') or '' for i in E.parse(resx).iter('data')}))
  for xlf in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
   originals[xlf.relative_to(source).as_posix()]=sha(xlf)
   tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language')
   values={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in tree.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
   localized=E.parse(resx)
   for i in localized.iter('data'):
    if i.get('name') in values:i.find('value').text=values[i.get('name')]
   folder=out/'satellites'/name/culture;folder.mkdir(parents=True)
   resource=folder/(logical+'.'+culture+'.resx');localized.write(resource,encoding='utf-8',xml_declaration=True)
   output=resource.with_suffix('.resources');E.SubElement(target,'GenerateResource',Sources=native(resource),OutputResources=native(output),ExecuteAsTool='false')
   resources.append(dict(assembly=name,resource=logical,culture=culture,strings={i.get('name'):i.findtext('value') or '' for i in localized.iter('data')}))
 rp=out/('localization-'+suffix+'.json');rp.write_text(json.dumps([r for r in resources if r['assembly']==name],ensure_ascii=False,indent=2)+'\n')
rp=out/'Resources.proj';E.ElementTree(project).write(rp,encoding='utf-8',xml_declaration=True)
resource_env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')))
run('resources',[sdkhost,'msbuild',native(rp),'-nologo','-t:Generate'],resource_env)
satellites={}
for r in resources:
 if not r['culture']:continue
 name=r['assembly'];culture=r['culture'];folder=out/'satellites'/name/culture
 info=folder/'AssemblyInfo.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]\n')
 destination=binary/culture/(name+'.resources.dll');destination.parent.mkdir(exist_ok=True)
 resource=folder/(r['resource']+'.'+culture+'.resources')
 compile('satellite-'+name+'-'+culture,[info],destination,refs,['/publicsign+','/keyfile:"'+native(build/'Roslyn.public.snk')+'"','/resource:"'+native(resource)+'",'+resource.name])
 satellites[destination.relative_to(binary).as_posix()]=sha(destination)
assert len(satellites)==26
coverage=dict(resource_sets=len(resources),resource_values=sum(len(r['strings']) for r in resources));assert coverage==dict(resource_sets=28,resource_values=39508)
(out/'original-localization-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
run('check-libraries',['/usr/bin/python3',str(here/'check-net10-libraries.py'),str(out)],dict(os.environ))
consumer=json.loads((out/'consumer-results.json').read_text())
record=dict(commands=commands+consumer['commands'],original_resources_and_api_inputs_sha256=originals,checker_inputs_sha256=consumer['checker_inputs_sha256'],satellite_files_sha256=satellites,coverage=coverage,net10_compiler_self_hosted_satellite_and_consumer_compilation=True,all_original_api_resource_analyzer_generator_pdb_checks_passed=True,formal_net10_compiler_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS 26 source NET10 satellites, all 10560 upstream APIs, 39508 strings, compiler/analyzer/generator/PDB checks')
