"""Freeze the standalone original task workflow reproducibly."""
from pathlib import Path
import gzip,hashlib,re,sys,tarfile

root=Path(__file__).resolve().parent;archive=root/'roslyn53-msbuild-tasks-source-2.tar.gz'
files=sorted(p for p in (root/'workflow').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
    for p in files:
        m=t.gettarinfo(str(p),'roslyn53-tasks-workflow/'+p.relative_to(root/'workflow').as_posix());m.mtime=m.uid=m.gid=0;m.uname=m.gname='';m.mode=0o644
        with p.open('rb') as f:t.addfile(m,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();recipe=root/'PKGBUILD';text=recipe.read_text();group=re.search(r'sha256sums=\((.*?)\)',text,re.S);items=list(re.finditer(r"'[^']*'",group[1]));assert len(items)==4
if sys.argv[1:]==['--update-checksum']:
    m=items[-1];text=text[:group.start(1)+m.start()]+"'"+digest+"'"+text[group.start(1)+m.end():];recipe.write_text(text)
else:assert not sys.argv[1:]
assert "'"+digest+"'" in text
print(len(files),'source workflow files SHA256',digest)
