"""Stage seven original NET10 TemplateEngine bootstrap archives and unresolved API evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as E
import zipfile

root, prefix = (Path(p).resolve() for p in sys.argv[1:])
prefix.mkdir()
here = Path(__file__).resolve().parent
name = 'dotnet-templateengine10-bootstrap'
doc = prefix / 'share/doc' / name
checks = doc / 'checks'
checks.mkdir(parents=True)
feed = prefix / 'lib/dotnet/library-packs'
feed.mkdir(parents=True)
binary = prefix / 'lib/dotnet10/library-packs/templateengine-10.0.200-preview.26113.113-net10-bootstrap/bin'
shutil.copytree(root / 'build/bin', binary)
records = json.loads((root / 'build/results.json').read_text())['projects']
models = json.loads((root / 'plan/evaluated.json').read_text())
source = Path(json.loads((root / 'plan/source-inputs.json').read_text())['source_root'])
for filename in ['Check.cs','CheckApi.cs','check.py','check-api-baseline.py','original-API-discrepancy.json','CheckResources.cs','check-resources.py','check-package-restore.py','check-installed.py']:
    shutil.copyfile(here / filename, checks / filename)
for record in records:
    for rel in record['original_resources']:
        resx = source / rel
        for file in [resx, *sorted((resx.parent / 'xlf').glob(resx.stem+'.*.xlf'))]:
            target = doc / 'validation-source' / file.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(file,target)
    for file in (source / 'src' / record['assembly']).glob('PublicAPI.*.txt'):
        target = doc / 'validation-source' / file.relative_to(source)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(file,target)
for src,dest in [('build/results.json','build-results.json'),('localized/results.json','localization-results.json'),('resource-check/results.json','resource-results.json'),('runtime-check/results.json','runtime-API-results.json'),('runtime-check/baseline-results.json','original-API-failure-results.json'),('dependencies/results.json','dependency-restore-results.json'),('source-audit.json','source-audit.json'),('plan/evaluated.json','evaluated-projects.json'),('flow/results.json','version-flow-results.json'),('public-api-analyzer-probe/results.json','additional-public-api-analyzer-probe.json')]:
    shutil.copyfile(root / src, doc / dest)
shutil.copyfile(here / 'README.package.md', doc / 'README.md')
archives = {}
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for record in records:
    assembly = record['assembly']
    package = E.Element('package')
    meta = E.SubElement(package,'metadata')
    for k,v in dict(id=assembly,version='10.0.200-preview.26113.113',authors='Microsoft',description='Original NET10 source-only TemplateEngine bootstrap; stronger all-seven API baseline retains two unresolved original entries',readme='README.md').items():E.SubElement(meta,k).text=v
    E.SubElement(meta,'license',type='expression').text='MIT'
    E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/dotnet',commit='05d9490471fb4b10d7ef4faa32c423e1b5adcaee')
    dependencies = E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0')
    for edge in record['original_project_edges']:
        if edge['metadata'].get('ReferenceOutputAssembly','true').lower()=='false':continue
        E.SubElement(dependencies,'dependency',id=edge['assembly'],version='[10.0.200-preview.26113.113]')
    central = {p['identity']:p['metadata']['Version'] for p in models[assembly]['items']['PackageVersion'] if p['metadata'].get('Version')}
    for edge in models[assembly]['items']['PackageReference']:
        if edge['metadata'].get('PrivateAssets','').lower()=='all':continue
        E.SubElement(dependencies,'dependency',id=edge['identity'],version=central[edge['identity']])
    members = {assembly+'.nuspec':E.tostring(package,encoding='utf-8',xml_declaration=True),'LICENSE.txt':(source/'LICENSE.txt').read_bytes(),'README.md':(here/'README.package.md').read_bytes()}
    for ext in record['output_sha256']:members['lib/net10.0/'+assembly+'.'+ext]=(binary/(assembly+'.'+ext)).read_bytes()
    for path in sorted(binary.glob('*/'+assembly+'.resources.dll')):members['lib/net10.0/'+path.relative_to(binary).as_posix()]=path.read_bytes()
    archive = feed / (assembly.lower()+'.10.0.200-preview.26113.113.nupkg')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for member,data in sorted(members.items()):
            item=zipfile.ZipInfo(member,(2000,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
    archives[assembly]=dict(archive=archive.relative_to(prefix).as_posix(),sha256=sha(archive),members={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
(doc/'archives.json').write_text(json.dumps(archives,indent=2)+'\n')
licenses=prefix/'share/licenses'/name;licenses.mkdir(parents=True)
for filename in ['LICENSE.txt','THIRD-PARTY-NOTICES.txt']:shutil.copyfile(source/filename,licenses/filename)
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS seven source NET10 archives,',len(manifest),'payload hashes; unresolved original API failure remains included')
