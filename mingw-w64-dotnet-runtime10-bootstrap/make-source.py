"""Export the complete source-only framework and package workflows reproducibly."""
from pathlib import Path
import gzip,hashlib,json,re,sys,tarfile

package=Path(__file__).resolve().parent;workflow=package.parent/'tests/runtime10-framework'
names=['README.md','prepare-source.py','prepare-version.py','prepare.py','evaluate.sh',
 'prepare-tools.py','build-tools.sh','prepare-templating.py','regenerate-asn.py','build.py',
 'audit-source.py','check-built.py','check-contracts.py','check-framework.py',
 'stage-framework.py','check-host.py','build-all.sh']
files=[(workflow/n,'framework-workflow/'+n) for n in names]
files += [(p,'framework-workflow/inputs/'+p.name) for p in sorted((workflow/'inputs').glob('*.cs'))]
files += [(package/n,'package-workflow/'+n) for n in ['README.md','dotnet10-bootstrap.sh','check-installed.py','stage-package.py']]
archive=package/'runtime10-bootstrap-source-1.tar.gz'
manifest={name:hashlib.sha256(path.read_bytes()).hexdigest() for path,name in files}
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
 for path,name in sorted(files,key=lambda p:p[1]):
  item=tar.gettarinfo(str(path),name);item.uid=item.gid=item.mtime=0;item.uname=item.gname='';item.mode=0o755 if path.suffix=='.sh' else 0o644
  with path.open('rb') as f:tar.addfile(item,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();recipe=package/'PKGBUILD';text=recipe.read_text()
if sys.argv[1:]==['--update-checksum']:
 group=re.search(r'sha256sums=\((.*?)\)',text,re.S);parts=list(re.finditer(r"'[^']*'",group[1]));assert len(parts)==3
 item=parts[2];a=group.start(1)+item.start();b=group.start(1)+item.end();text=text[:a]+"'"+digest+"'"+text[b:];recipe.write_text(text)
else:assert not sys.argv[1:],'usage: make-source.py [--update-checksum]'
assert digest in text,('Workflow changed; review and freeze the new source archive',digest)
(package/'workflow-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(digest,len(files),'source workflow files',archive.name)
