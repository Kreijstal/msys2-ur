"""Stage the original NET8 Immutable8 archive with original identities and validation inputs."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);records=json.loads((root/'build/results.json').read_text());name='dotnet-immutable8';doc=prefix/'share/doc'/name;checks=doc/'checks';checks.mkdir(parents=True);feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);binary=prefix/'lib/dotnet10/library-packs/immutable-8.0.0-net8-bootstrap/bin';shutil.copytree(root/'build/bin',binary);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['check-restore.py','check.py','Check.cs','check-resources.py','CheckResources.cs','check-api.py','CompareApi.cs','check-installed.py','Microsoft.pubkey.hex']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for r in records['projects']:
 for rel in r['original_resources']:
  p=source/rel
  for f in [p,*sorted((p.parent/'xlf').glob(p.stem+'.*.xlf'))]:
   dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
 if r['original_framework']=='net8.0':
  for f in (source/'src/libraries'/r['assembly']/'ref').glob('*'):
   if f.is_file():dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
for src,dest in [(root/'build/results.json','build-results.json'),(root/'localized/results.json','localization-results.json'),(root/'source-audit.json','source-audit.json'),(root/'resource-check/results.json','resource-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'api-check/results.json','api-results.json'),(root/'plan/source-inputs.json','source-inputs.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/dest)
archives={};project_names={r['assembly'] for r in records['projects']}
for r in records['projects']:
 if r['original_framework']!='net8.0':continue
 assembly=r['assembly'];package=E.Element('package');meta=E.SubElement(package,'metadata')
 for k,v in dict(id=assembly,version='8.0.0',authors='Microsoft',description='Exact Immutable8.0.0 original NET8 source bootstrap').items():E.SubElement(meta,k).text=v
 E.SubElement(meta,'license',type='expression').text='MIT';E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/runtime',commit='5535e31a712343a63f5d7d796cd874e563e5ac14');deps=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
 for edge in r['original_project_edges']:
  if edge['metadata'].get('ReferenceOutputAssembly','true').lower()=='false':continue
  assert edge['project'] in ['System.Collections','System.Memory','System.Runtime','System.Runtime.InteropServices','System.Runtime.Numerics','System.Text.Encoding.Extensions'] # Original NET10 inbox project references are satisfied by the framework.
 members={assembly+'.nuspec':E.tostring(package,encoding='utf-8',xml_declaration=True),'LICENSE.TXT':(source/'LICENSE.TXT').read_bytes()}
 for ext in r['output_sha256']:members['lib/net8.0/'+assembly+'.'+ext]=(binary/(assembly+'.'+ext)).read_bytes()
 archive=feed/(assembly.lower()+'.8.0.0.nupkg')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for member,data in members.items():
   i=zipfile.ZipInfo(member,(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
 archives[assembly]=dict(archive=archive.relative_to(prefix).as_posix(),sha256=sha(archive),members={k:hashlib.sha256(v).hexdigest() for k,v in members.items()})
(doc/'archives.json').write_text(json.dumps(archives,indent=2)+'\n');licenses=prefix/'share/licenses'/name;licenses.mkdir(parents=True)
for n in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:shutil.copyfile(source/n,licenses/n)
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS original NET8 Immutable8 archive and',len(manifest),'payload hashes')
