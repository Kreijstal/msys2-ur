"""Freeze the complete standalone compiler workflow into a deterministic archive."""
from pathlib import Path
import gzip,hashlib,re,sys,tarfile
root=Path(__file__).resolve().parent
files=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in {'make-source.py','PKGBUILD','.SRCINFO'} and p.suffix not in {'.gz','.pyc','.nupkg','.zst'} and p.relative_to(root).parts[0] not in {'src','pkg'} )
archive=root/'eventlog9-source-1.tar.gz'
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
 for p in files:
  info=tar.gettarinfo(str(p),'eventlog9-workflow/'+p.relative_to(root).as_posix());info.mtime=info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o755 if p.suffix=='.sh' or p.name=='csc53-bootstrap' else 0o644
  with p.open('rb') as f:tar.addfile(info,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();recipe=root/'PKGBUILD';text=recipe.read_text()
if sys.argv[1:]==['--update-checksum']:
 group=re.search(r'sha256sums=\((.*?)\)',text,re.S);items=list(re.finditer(r"'[^']*'",group[1]));assert len(items)==4
 item=items[2];text=text[:group.start(1)+item.start()]+"'"+digest+"'"+text[group.start(1)+item.end():];recipe.write_text(text)
else:assert not sys.argv[1:]
assert "'"+digest+"'" in text,digest
print(len(files),'workflow files SHA256',digest)
