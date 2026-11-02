"""Independently verify original documentation baselines and shipped text assets."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import zipfile

root,out=(Path(p).resolve() for p in sys.argv[1:])
manifest=json.loads((out/'source-inputs.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
selected={commit:{} for commit in manifest['archives']}
for name,record in manifest['projects'].items():
    source=out/('maintenance-packages-'+record['commit'])
    wanted=selected[record['commit']]
    for relative in ['LICENSE','Directory.Build.props','Directory.Build.targets','eng/resources.targets',
                     'src/'+name+'/src/'+name+'.xml','src/'+name+'/src/PACKAGE.md']:
        file=source/relative;assert file.is_file(),file
        wanted[relative]=sha(file.read_bytes())
    with zipfile.ZipFile(out/'feed'/(name+'.'+record['version']+'.nupkg')) as z:
        for relative,target in [('LICENSE','LICENSE'),('src/'+name+'/src/PACKAGE.md','PACKAGE.md'),('src/'+name+'/src/'+name+'.xml','lib/netstandard2.0/'+name+'.xml')]:
            assert z.read(target)==(source/relative).read_bytes(),(name,target)
audits={}
for commit,(filename,digest) in manifest['archives'].items():
    archive=root/filename;assert sha(archive.read_bytes())==digest
    verified=set()
    with tarfile.open(archive) as tar:
        assert tar.pax_headers['comment']==commit
        for member in tar:
            relative=member.name.partition('/')[2]
            if member.isfile() and relative in selected[commit]:
                assert sha(tar.extractfile(member).read())==selected[commit][relative],relative
                verified.add(relative)
    assert verified==set(selected[commit]),commit
    audits[commit]=dict(original_assets_verified=len(verified),sha256=selected[commit])
(out/'asset-audit.json').write_text(json.dumps(dict(archives=audits,all_five_package_licenses_readmes_and_xml_docs_match_original_sources=True),indent=2)+'\n')
print('PASS pinned original XML documentation baselines, build/resource policies and all five shipped licenses/readmes/docs')
