"""Export original source-only NuGet content for every declared framework, with byte audit."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive,version,out=Path(sys.argv[1]).resolve(),sys.argv[2],Path(sys.argv[3]).resolve()
out.mkdir()
here=Path(__file__).resolve().parent
contract=json.loads((here/'original-source-contracts.json').read_text())[version]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)==contract['source_archive_sha256']
source=out/'source';source.mkdir()
originals={}
with tarfile.open(archive) as t:
    prefix='wcwidth-'+contract['source_commit']+'/'
    for m in t:
        if not m.isfile():continue
        assert m.name.startswith(prefix)
        rel=m.name[len(prefix):]
        if Path(rel).suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.snk','.obj','.a','.lib'}:continue
        target=source/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(t.extractfile(m).read());originals[rel]=sha(target)
project=source/'src/Wcwidth.Sources/Wcwidth.Sources.csproj'
assert sha(project)==contract['source_csproj_sha256']
model=E.parse(project);tfms=model.findtext('.//TargetFrameworks').split(';')
assert tfms==contract['original_source_frameworks']
assert model.findtext('.//PackBuildOutput')=='false' and model.findtext('.//TreatWarningsAsErrors')=='true'
compile_item=model.find('.//Compile');assert compile_item.get('Include')=='..\\Wcwidth\\**\\*.cs' and compile_item.get('Link')=='External\\Wcwidth\\%(RecursiveDir)%(Filename)%(Extension)'
production=source/'src/Wcwidth'
files=sorted(p for p in production.rglob('*.cs') if 'obj' not in p.relative_to(production).parts)
assert len(files)==(7 if version=='2.0.0' else 9)
package=E.Element('package');meta=E.SubElement(package,'metadata')
for k,v in dict(id='Wcwidth.Sources',version=version,authors='Patrik Svensson and contributors',description='Original source-only Wcwidth content for console Unicode cell widths').items():E.SubElement(meta,k).text=v
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/spectreconsole/wcwidth',commit=contract['source_commit'])
content=E.SubElement(meta,'contentFiles');members={};content_hashes={}
for tfm in tfms:
    for path in files:
        member='contentFiles/cs/'+tfm+'/External/Wcwidth/'+path.relative_to(production).as_posix()
        assert sha(path)==contract['content_files'][member],member
        members[member]=path.read_bytes();content_hashes[member]=sha(path)
        E.SubElement(content,'files',include=member,buildAction='Compile')
assert content_hashes==contract['content_files']
license=next(p for p in source.iterdir() if p.name.lower() in {'license','license.md','license.txt'})
members['LICENSE.txt']=license.read_bytes()
members['Wcwidth.Sources.nuspec']=E.tostring(package,encoding='utf-8',xml_declaration=True)
feed=out/'feed';feed.mkdir();target=feed/('wcwidth.sources.'+version+'.nupkg')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(members.items()):
        item=zipfile.ZipInfo(name,(2000,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
(out/'results.json').write_text(json.dumps(dict(version=version,source_commit=contract['source_commit'],source_archive_sha256=sha(archive),source_files_sha256=originals,original_source_changes=0,original_source_frameworks=tfms,original_production_source_sha256={p.relative_to(production).as_posix():sha(p) for p in files},content_file_sha256=content_hashes,original_generated_tables_retained=True,production_project_does_not_invoke_table_generator=True,archive=target.as_posix(),archive_sha256=sha(target),archive_members={n:hashlib.sha256(b).hexdigest() for n,b in members.items()},original_source_profiles_preserved=True,original_MinVer_NuGetizer_analyzers_toolchain_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',version,len(files),'original source files,',len(content_hashes),'exact content entries and all',len(tfms),'source frameworks')
