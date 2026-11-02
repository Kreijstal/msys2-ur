"""Reproduce the frozen source workflow, excluding generated validation evidence."""
from pathlib import Path
import gzip, hashlib, io, sys, tarfile

source = Path(__file__).resolve().parent.parent / 'tests/protecteddata44'
destination = Path(sys.argv[1]).resolve()
with destination.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode='w') as t:
    for p in sorted(source.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        selected = (p.suffix in {'.py', '.cs', '.hex', '.md', '.patch', '.props', '.targets'}
            or p.name == 'empty-input-fix-upstream.cs.txt'
            or p.name == 'source-inputs.json' and p.parent.name == 'buildtools-resource-helper')
        if not selected:
            continue
        data = p.read_bytes()
        m = tarfile.TarInfo('protecteddata44-workflow/' + p.relative_to(source).as_posix())
        m.size = len(data)
        m.mode = 0o644
        t.addfile(m, io.BytesIO(data))
print(hashlib.sha256(destination.read_bytes()).hexdigest())
