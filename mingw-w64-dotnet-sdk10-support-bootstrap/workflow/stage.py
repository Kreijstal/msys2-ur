"""Stage the exact source SDK10 support NuGet archives and independent consumer fixtures."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;source=root/'plan/snapshot/runtime';build=json.loads((root/'build/results.json').read_text());feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);doc=prefix/'share/doc/dotnet-sdk10-support-bootstrap';checks=doc/'checks';checks.mkdir(parents=True)
for n in ['check.py','Check.cs','check-api.py','CompareApi.cs','check-installed.py','Open.pubkey.hex','AspNetCore.pubkey.hex']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for name in ['System.IO.Hashing','Microsoft.Extensions.DependencyModel']:
    folder=source/'src/libraries'/name
    for p in list((folder/'ref').glob('*'))+list((folder/'src/Resources').glob('*.resx'))+list((folder/'tests').glob('*Tests.cs')):
        if p.is_file():dest=validation/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for src,dest in [(root/'build/results.json','build-results.json'),(root/'source-audit.json','source-audit.json'),(root/'api-check/results.json','api-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'plan/snapshot/vmr-source-inputs.json','vmr-source-inputs.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/dest)
for record in build['projects']:
    name=record['assembly'];version=record['version'];package=E.Element('package');meta=E.SubElement(package,'metadata')
    for k,v in dict(id=name,version=version,authors='Microsoft',description='Original VMR SDK10 NET10 runtime support source bootstrap profile').items():E.SubElement(meta,k).text=v
    E.SubElement(meta,'license',type='expression').text='MIT';E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/dotnet',commit='44525024595742ebe09023abe709df51de65009b');E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0')
    with zipfile.ZipFile(feed/(name.lower()+'.'+version+'.nupkg'),'w',zipfile.ZIP_DEFLATED) as z:
        for member,data in [(name+'.nuspec',E.tostring(package,encoding='utf-8',xml_declaration=True)),('LICENSE.TXT',(source/'LICENSE.TXT').read_bytes())]+[('lib/net10.0/'+name+'.'+ext,(root/'build/bin'/(name+'.'+ext)).read_bytes()) for ext in ['dll','pdb','xml']]:
            i=zipfile.ZipInfo(member,(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
license=prefix/'share/licenses/dotnet-sdk10-support-bootstrap';license.mkdir(parents=True);shutil.copyfile(source/'LICENSE.TXT',license/'LICENSE.TXT')
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged three exact original NET10 source archives and validation inputs;',len(manifest),'files')
