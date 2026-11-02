"""Freeze the reference9 workflow deterministically."""
from pathlib import Path
import gzip,hashlib,re,sys,tarfile
root=Path(__file__).resolve().parent;source=root.parent/'tests/reference9'
files=sorted([p for p in source.iterdir() if p.is_file() and p.suffix in {'.py','.sh','.md','.json'} and 'results' not in p.name]+[p for p in (source/'inputs').iterdir() if p.is_file()])
archive=root/'reference9-source-1.tar.gz'
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
 for p in files:
  info=t.gettarinfo(str(p),'reference9-workflow/'+p.relative_to(source).as_posix());info.mtime=info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o755 if p.suffix=='.sh' else 0o644
  with p.open('rb') as f:t.addfile(info,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();recipe=root/'PKGBUILD';s=recipe.read_text();group=re.search(r'sha256sums=\((.*?)\)',s,re.S);items=list(re.finditer(r"'[^']*'",group[1]));assert len(items)==3
if sys.argv[1:]==['--update-checksum']:
 item=items[2];s=s[:group.start(1)+item.start()]+"'"+digest+"'"+s[group.start(1)+item.end():];recipe.write_text(s)
else:assert not sys.argv[1:]
assert "'"+digest+"'" in s,digest
print(len(files),'workflow files SHA256',digest)
