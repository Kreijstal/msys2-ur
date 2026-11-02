from pathlib import Path
import gzip,hashlib,io,tarfile
root=Path(__file__).resolve().parent;buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as t:
    for p in sorted((root/'workflow').iterdir()):
        if not p.is_file():continue
        data=p.read_bytes();i=tarfile.TarInfo('nuget73-libraries-workflow/'+p.name);i.size=len(data);i.mode=0o644;i.mtime=0;t.addfile(i,io.BytesIO(data))
archive=root/'nuget73-libraries-source-2.tar.gz';archive.write_bytes(gzip.compress(buffer.getvalue(),mtime=0));print(hashlib.sha256(archive.read_bytes()).hexdigest(),archive.name)
