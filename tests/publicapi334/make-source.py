"""Bundle the checked-in source workflow deterministically for makepkg."""
from pathlib import Path
import gzip
import hashlib
import io
import sys
import tarfile

here = Path(__file__).resolve().parent
output = Path(sys.argv[1]).resolve()
files = sorted((p for p in here.iterdir() if p.suffix in {'.py','.cs','.patch','.hex'} or p.name == 'README.md'), key=lambda p:p.name)
with output.open('wb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', mtime=0, filename='') as compressed:
    with tarfile.open(fileobj=compressed, mode='w') as archive:
        for path in files:
            data = path.read_bytes()
            item = tarfile.TarInfo('publicapi334-workflow/' + path.name)
            item.size = len(data)
            item.mode = 0o644
            archive.addfile(item, io.BytesIO(data))
print(hashlib.sha256(output.read_bytes()).hexdigest())
