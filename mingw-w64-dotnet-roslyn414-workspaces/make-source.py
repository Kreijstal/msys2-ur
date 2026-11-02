"""Produce a deterministic archive containing the standalone runtime9 build workflow."""
from pathlib import Path
import gzip
import hashlib
import re
import sys
import tarfile

root=Path(__file__).resolve().parent
files=sorted([p for p in root.iterdir() if p.is_file() and p.name!='make-source.py' and p.suffix in {'.py','.sh','.md'}]
             +[p for p in (root/'inputs').iterdir() if p.is_file()])
archive=root/'workspaces414-source-1.tar.gz'
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
    for p in files:
        info=t.gettarinfo(str(p),'workspaces414-workflow/'+p.relative_to(root).as_posix());info.mtime=info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o755 if p.suffix=='.sh' else 0o644
        with p.open('rb') as f:t.addfile(info,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();recipe=root/'PKGBUILD';text=recipe.read_text()
if sys.argv[1:]==['--update-checksum']:
    group=re.search(r'sha256sums=\((.*?)\)',text,re.S);assert group
    matches=list(re.finditer(r"'[^']*'",group[1]));assert len(matches)==2
    old=matches[1];a=group.start(1)+old.start();b=group.start(1)+old.end();text=text[:a]+"'"+digest+"'"+text[b:];recipe.write_text(text)
else:assert not sys.argv[1:],'usage: make-source.py [--update-checksum]'
assert "'"+digest+"'" in text,digest
print(digest,len(files),'workflow files',archive.name)
