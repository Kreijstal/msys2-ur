"""Build all original VB satellites and run the full NET10 compiler/API suite."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,re,shutil,subprocess,sys,xml.etree.ElementTree as E
source,plan,clients,vb,out=(Path(p).resolve() for p in sys.argv[1:6]);assert not out.exists();out.mkdir()
here=Path(__file__).resolve().parent
@lru_cache(maxsize=None)
def native(p):
 s=str(p).replace('\\','/')
 if re.match(r'^/[a-zA-Z]/',s):return s[1].upper()+':'+s[2:]
 if s.startswith('/clang64/'):return native(Path('/clang64'))+s[len('/clang64'):]
 return subprocess.check_output(['cygpath','-am',s],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binary=out/'bin';shutil.copytree(clients/'bin',binary)
assert sha(binary/'Microsoft.CodeAnalysis.VisualBasic.dll')==json.loads((vb/'results.json').read_text())['output_sha256']
main=source/'src/Compilers/VisualBasic/Portable';resx=main/'VBResources.resx';logical='Microsoft.CodeAnalysis.VisualBasic.VBResources';originals={resx.relative_to(source).as_posix():sha(resx)}
resources=[dict(assembly='Microsoft.CodeAnalysis.VisualBasic',resource=logical,culture='',strings={i.get('name'):i.findtext('value') or '' for i in E.parse(resx).iter('data')})]
rp=E.Element('Project');target=E.SubElement(rp,'Target',Name='Generate');ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
for xlf in sorted((resx.parent/'xlf').glob('VBResources.*.xlf')):
 originals[xlf.relative_to(source).as_posix()]=sha(xlf);tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language')
 values={i.get('id'):''.join(i.find('x:target',ns).itertext()) for i in tree.findall('.//x:trans-unit',ns) if i.find('x:target',ns) is not None}
 localized=E.parse(resx)
 for i in localized.iter('data'):
  if i.get('name') in values:i.find('value').text=values[i.get('name')]
 folder=out/'satellites'/culture;folder.mkdir(parents=True);file=folder/('VBResources.'+culture+'.resx');localized.write(file,encoding='utf-8',xml_declaration=True)
 E.SubElement(target,'GenerateResource',Sources=native(file),OutputResources=native(file.with_suffix('.resources')),ExecuteAsTool='false')
 resources.append(dict(assembly='Microsoft.CodeAnalysis.VisualBasic',resource=logical,culture=culture,strings={i.get('name'):i.findtext('value') or '' for i in localized.iter('data')}))
assert len(resources)==14
(out/'localization.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
resource_project=out/'Resources.proj';E.ElementTree(rp).write(resource_project,encoding='utf-8',xml_declaration=True)
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable');commands=[]
def run(label,command,environment=env):
 with (out/(label+'.log')).open('w') as f:r=subprocess.run(command,env=environment,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
sdk_env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')))
run('resources',['/clang64/lib/dotnet/dotnet.exe','msbuild',native(resource_project),'-nologo','-t:Generate'],sdk_env)
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
def compile(label,files,output,extras=()):
 args=['/nostdlib+','/target:library','/langversion:preview','/nullable:enable','/deterministic+','/debug:portable','/out:"'+native(output)+'"',*extras]
 args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in files]
 rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n');run(label,[host,native(binary/'csc.dll'),'-noconfig','@'+native(rsp)])
satellites={}
for entry in resources[1:]:
 culture=entry['culture'];folder=out/'satellites'/culture;info=folder/'AssemblyInfo.cs'
 info.write_text('[assembly:System.Reflection.AssemblyVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("5.3.0.0")]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v10.0")]\n')
 dest=binary/culture/'Microsoft.CodeAnalysis.VisualBasic.resources.dll';dest.parent.mkdir(exist_ok=True)
 compile('satellite-'+culture,[info],dest,['/publicsign+','/keyfile:"'+native(vb/'Roslyn.public.snk')+'"','/resource:"'+native(folder/('VBResources.'+culture+'.resources'))+'",'+logical+'.'+culture+'.resources'])
 satellites[dest.relative_to(binary).as_posix()]=sha(dest)
api=[]
for name in ['PublicAPI.Shipped.txt','PublicAPI.Unshipped.txt']:
 p=main/name;originals[p.relative_to(source).as_posix()]=sha(p);api.append(p.read_text().rstrip())
(out/'api-vb.txt').write_text('\n'.join(api)+'\n')
model=json.loads((plan/'evaluated.json').read_text())['Microsoft.CodeAnalysis.VisualBasic'];key=(vb/'Roslyn.public.snk').read_bytes().hex()
friends=[i['identity']+', PublicKey='+(i['metadata'].get('Key') or key) for i in model['items']['InternalsVisibleTo']]
(out/'friends.json').write_text(json.dumps(dict(friends=friends),indent=2)+'\n')
shutil.copyfile(binary/'csc.runtimeconfig.json',binary/'VBChecks.runtimeconfig.json')
run('check-libraries',['/usr/bin/python3',str(here/'check-net10-vb-libraries.py'),str(source),str(out)],dict(os.environ))
files=sorted((here/'vb-check-inputs').glob('*.cs'));assert len(files)==3
consumer=json.loads((out/'consumer-results.json').read_text());commands+=consumer['commands']
record=dict(commands=commands,original_source_inputs_sha256=originals,satellite_files_sha256=satellites,checker_inputs_sha256={p.name:sha(p) for p in files},original_resource_sets=len(resources),original_resource_strings=sum(len(i['strings']) for i in resources),all_original_vb_api_and_resources_passed=True,compiler_server_execution_verified=False,full_toolset_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS NET10 VB compiler original API,14 resource sets/'+str(record['original_resource_strings'])+' strings,13 satellites and full compiler behavior suite')
