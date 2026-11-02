"""Recreate the deterministic source workflow archive used by PKGBUILD."""
from pathlib import Path
import gzip,hashlib,io,tarfile
root=Path(__file__).resolve().parent;buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as tar:
    for path in sorted((root/'workflow').iterdir()):
        if not path.is_file():continue
        data=path.read_bytes();info=tarfile.TarInfo('newtonsoft1303-workflow/'+path.name);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
archive=root/'newtonsoft1303-source-2.tar.gz';archive.write_bytes(gzip.compress(buffer.getvalue(),mtime=0));print(hashlib.sha256(archive.read_bytes()).hexdigest(),archive.name)
