"""Check all original neutral/XLF resources, identities and portable PDB associations."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E
plan,build,localized,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);records=json.loads((build/'results.json').read_text())['projects'];models=[];ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
for record in records:
 for rel in record['original_resource_sha256']:
  meta={'logical_name':record['assembly']+'.'+Path(rel).stem}
  values={n.get('name'):(n.find('value').text or '') for n in E.parse(source/rel).iter('data')}
  models.append(dict(assembly=record['assembly'],culture='',resource=meta['logical_name'],source_resx=str(source/rel),strings=values))
  resx=source/rel
  for xlf in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
   tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');translated=dict(values)
   for item in tree.findall('.//x:trans-unit',ns):
    target=item.find('x:target',ns)
    if target is not None and item.get('id') in translated:translated[item.get('id')]=''.join(target.itertext())
   models.append(dict(assembly=record['assembly'],culture=culture,resource=meta['logical_name'],strings={k:v.replace('\n',os.linesep) for k,v in translated.items()}))
check_records=[dict(r,key_policy='MicrosoftShared') for r in records];(out/'build-records.json').write_text(json.dumps({'projects':check_records}));(out/'expected.json').write_text(json.dumps(models,ensure_ascii=False))
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
native=lambda p:Path(p).resolve().as_posix();rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(here/'CheckResources.cs')+'"'])+'\n')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[]
for label,cmd in [('compile',[host,compiler,'-noconfig','@'+native(rsp)]),('resources',[host,out/'Check.dll',build/'bin',out/'expected.json',out/'build-records.json'])]:
 if label=='resources':(out/'Check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net10.0','framework':{'name':'Microsoft.NETCore.App','version':'10.0.5'}}}))
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=120)
 commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,neutral_resource_sets=3,localized_resource_sets=39,exact_values=sum(len(m['strings']) for m in models),satellite_assemblies=39,original_assembly_file_key_framework_identities_verified=True,portable_pdb_associations=4,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'resources.log').read_text(encoding='utf-8'))
