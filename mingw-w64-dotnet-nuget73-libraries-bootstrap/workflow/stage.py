"""Stage the eight original NET10 NuGet libraries,documentation and localization."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent
runtime=prefix/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';binary=runtime/'bin';binary.mkdir(parents=True)
result=json.loads((root/'build/results.json').read_text());names=[p['assembly'] for p in result['projects']];assert len(names)==8
for name in names:
    for ext in ['dll','pdb','xml']:shutil.copyfile(root/'build/bin'/(name+'.'+ext),binary/(name+'.'+ext))
local=json.loads((root/'localized-closure/results.json').read_text())
for rel,h in local['satellite_sha256'].items():
    src=root/'build/bin'/rel;assert hashlib.sha256(src.read_bytes()).hexdigest()==h
    dest=binary/rel;dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
doc=prefix/'share/doc/dotnet-nuget73-libraries-bootstrap';checks=doc/'checks';checks.mkdir(parents=True)
for n in ['check-installed.py','check-closure.py','CheckClosure.cs','CheckApi.cs','check-packaged-restore.py','PackagedRestore.cs']:shutil.copyfile(here/n,checks/n)
source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);validation=doc/'validation-source'
for name in names:
    folder=source/'src/NuGet.Core'/name
    for p in list(folder.glob('*.resx'))+list(folder.rglob('PublicAPI.*.txt')):
        dest=validation/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for rel,dest in [('source-audit.json','source-audit.json'),('build/results.json','build-results.json'),('localized-closure/results.json','localization-results.json'),('localized-closure/expected.json','expected-localization.json')]:shutil.copyfile(root/rel,doc/dest)
shutil.copyfile(here/'README.md',doc/'README.md');license_dir=prefix/'share/licenses/dotnet-nuget73-libraries-bootstrap';license_dir.mkdir(parents=True);shutil.copyfile(source/'LICENSE.txt',license_dir/'LICENSE.txt')
model=json.loads((root/'plan/evaluated.json').read_text());version='7.3.0-preview.1.11413';external={'Newtonsoft.Json':'13.0.3','System.Security.Cryptography.Pkcs':'8.0.1','System.Security.Cryptography.ProtectedData':'8.0.0','Microsoft.Extensions.FileSystemGlobbing':'6.0.0','Microsoft.Extensions.FileProviders.Abstractions':'6.0.0'}
feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True)
for name in names:
    entry=model[name];deps={Path(p['full_path']).stem:version for p in entry['items']['ProjectReference']}
    deps.update({p['identity']:external[p['identity']] for p in entry['items']['PackageReference']})
    package=E.Element('package');meta=E.SubElement(package,'metadata')
    for key,value in dict(id=name,version=version,authors='Microsoft',description='Original VMR NET10 NuGet7.3 source bootstrap profile').items():E.SubElement(meta,key).text=value
    E.SubElement(meta,'license',type='expression').text='Apache-2.0';E.SubElement(meta,'repository',type='git',url='https://github.com/NuGet/NuGet.Client',commit='bf048eb714eb6b1912ba868edca4c7cfec454841')
    group=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0')
    for dep,v in deps.items():E.SubElement(group,'dependency',id=dep,version='['+v+']')
    with zipfile.ZipFile(feed/(name.lower()+'.'+version+'.nupkg'),'w',zipfile.ZIP_DEFLATED) as z:
        for member,data in [(name+'.nuspec',E.tostring(package,encoding='utf-8',xml_declaration=True)),('LICENSE.txt',(source/'LICENSE.txt').read_bytes())]+[('lib/net10.0/'+name+'.'+ext,(binary/(name+'.'+ext)).read_bytes()) for ext in ['dll','pdb','xml']]:
            info=zipfile.ZipInfo(member,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS staged eight NuGet7.3 libraries,XML documentation,104 satellites and eight exact-dependency source archives;',len(manifest),'files')
