"""Stage seven original NuGet6.13.2 NET10 libraries and unchanged dependency requirements."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);records=json.loads((root/'build/results.json').read_text());models=json.loads((root/'plan/evaluated.json').read_text());name='dotnet-nuget6132-template-bootstrap';doc=prefix/'share/doc'/name;checks=doc/'checks';checks.mkdir(parents=True);feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);binary=prefix/'lib/dotnet10/library-packs/nuget-6.13.2-net10-template-bootstrap/bin';binary.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['check.py','Check.cs','CheckApi.cs','check-resources.py','CheckResources.cs','check-installed.py','check-package-restore.py']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for r in records['projects']:
 for rel in r['original_resource_sha256']:
  if rel.endswith('.resx'):
   p=source/rel;dest=validation/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 folder=source/'src/NuGet.Core'/r['assembly']
 for p in folder.glob('**/PublicAPI*.txt'):
  dest=validation/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 for ext in ['dll','pdb','xml']:shutil.copyfile(root/'build/bin'/(r['assembly']+'.'+ext),binary/(r['assembly']+'.'+ext))
for src,dest in [(root/'build/results.json','build-results.json'),(root/'localized/results.json','localization-results.json'),(root/'source-audit.json','source-audit.json'),(root/'resource-check/results.json','resource-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'dependencies/results.json','dependency-restore-results.json'),(root/'plan/source-inputs.json','source-inputs.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/dest)
archives={}
for r in records['projects']:
 assembly=r['assembly'];package=E.Element('package');meta=E.SubElement(package,'metadata')
 for k,v in dict(id=assembly,version='6.13.2',authors='Microsoft',description='Original NuGet6.13.2 NET10 source-only profile; source dependency restore diagnostics retained').items():E.SubElement(meta,k).text=v
 E.SubElement(meta,'license',type='expression').text='Apache-2.0';E.SubElement(meta,'repository',type='git',url='https://github.com/NuGet/NuGet.Client',commit='5d81cb8da82eda8a6b47aae92d1e6f888de982ce');deps=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0')
 for edge in models[assembly]['items']['ProjectReference']:E.SubElement(deps,'dependency',id=Path(edge['full_path']).stem,version='[6.13.2]')
 central={i['identity']:i['metadata']['Version'] for i in models[assembly]['items']['PackageVersion'] if i['metadata'].get('Version')}
 for edge in models[assembly]['items']['PackageReference']:E.SubElement(deps,'dependency',id=edge['identity'],version=central[edge['identity']])
 members={assembly+'.nuspec':E.tostring(package,encoding='utf-8',xml_declaration=True),'LICENSE.txt':(source/'LICENSE.txt').read_bytes()}
 for ext in ['dll','pdb','xml']:members['lib/net10.0/'+assembly+'.'+ext]=(binary/(assembly+'.'+ext)).read_bytes()
 archive=feed/(assembly.lower()+'.6.13.2.nupkg')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for member,data in members.items():
   info=zipfile.ZipInfo(member,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
 archives[assembly]=dict(archive=archive.relative_to(prefix).as_posix(),sha256=sha(archive),members={k:hashlib.sha256(v).hexdigest() for k,v in members.items()})
(doc/'archives.json').write_text(json.dumps(archives,indent=2)+'\n');licenses=prefix/'share/licenses'/name;licenses.mkdir(parents=True);shutil.copyfile(source/'LICENSE.txt',licenses/'LICENSE.txt')
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS seven original NET10 NuGet6.13.2 archives and',len(manifest),'payload hashes')
