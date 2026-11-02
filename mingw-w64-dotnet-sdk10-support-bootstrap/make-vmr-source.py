"""Freeze the acquired and verified VMR support-source view reproducibly."""
from pathlib import Path
import gzip,hashlib,io,json,sys,tarfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;manifest=json.loads((root/'snapshot-sha256.json').read_text());buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as t:
    for rel in sorted([*manifest,'snapshot-sha256.json']):
        data=(root/rel).read_bytes()
        if rel in manifest:assert hashlib.sha256(data).hexdigest()==manifest[rel]
        i=tarfile.TarInfo(rel);i.size=len(data);i.mode=0o644;i.mtime=0;t.addfile(i,io.BytesIO(data))
p=here/'runtime-sdk10-vmr-44525024.tar.gz';p.write_bytes(gzip.compress(buffer.getvalue(),mtime=0));print(hashlib.sha256(p.read_bytes()).hexdigest(),p.name)
