"""Freeze the exact VMR deployment/reference-source view reproducibly."""
from pathlib import Path
import gzip,hashlib,io,json,sys,tarfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;origin=json.loads((root/'source-inputs.json').read_text());buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as t:
    for rel in sorted([*origin['files'],'source-inputs.json']):
        data=(root/rel).read_bytes()
        if rel!='source-inputs.json':assert hashlib.sha256(data).hexdigest()==origin['files'][rel]['sha256'],rel
        info=tarfile.TarInfo(rel);info.size=len(data);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(data))
p=here/'deployment-releases-vmr-44525024.tar.gz';p.write_bytes(gzip.compress(buffer.getvalue(),mtime=0));print(hashlib.sha256(p.read_bytes()).hexdigest(),p.name)
