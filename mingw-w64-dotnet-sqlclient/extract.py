"""Verify and extract the complete pinned maintenance-packages source archive."""
from pathlib import Path
import hashlib,shutil,sys,tarfile
archive,out=(Path(p) for p in sys.argv[1:])
with archive.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='f5b1bd0cf8b2c6e232ff866a4f3b069c30c48f37820c10c81691de211d4ba3c6'
out.mkdir()
with tarfile.open(archive,'r|gz') as t:
    for m in t:
        if m.isdir():continue
        assert m.isfile(),m.name
        prefix,path=m.name.split('/',1)
        assert prefix=='maintenance-packages-84b081710c66cc560b77d4de38cee493c3a38e9d'
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        dest=out/path;dest.parent.mkdir(parents=True,exist_ok=True)
        with t.extractfile(m) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
print('PASS complete pinned maintenance-packages source archive hash and extraction')
