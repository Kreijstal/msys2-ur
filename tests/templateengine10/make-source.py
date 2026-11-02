"""Bundle the reproducible TemplateEngine bootstrap workflow and pinned VMR flow policy."""
from pathlib import Path
import gzip
import hashlib
import io
import sys
import tarfile

here = Path(__file__).resolve().parent
output = Path(sys.argv[1]).resolve()
files = [p for p in here.iterdir() if p.suffix in {'.py','.cs','.hex'} or p.name in {'README.package.md','original-API-discrepancy.json'}]
files += [p for p in (here/'version-flow-policy').rglob('*') if p.is_file()]
with output.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as compressed:
    with tarfile.open(fileobj=compressed,mode='w') as archive:
        for path in sorted(files,key=lambda p:p.relative_to(here).parts):
            data=path.read_bytes();item=tarfile.TarInfo('templateengine10-workflow/'+path.relative_to(here).as_posix());item.size=len(data);item.mode=0o644;archive.addfile(item,io.BytesIO(data))
print(hashlib.sha256(output.read_bytes()).hexdigest())
