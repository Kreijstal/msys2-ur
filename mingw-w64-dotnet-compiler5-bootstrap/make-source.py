"""Create the deterministic local source archive and check the recipe digest."""
from pathlib import Path
import gzip
import hashlib
import tarfile

root = Path(__file__).resolve().parent
files = [root / name for name in (
    'README.md', 'audit.py', 'build.sh', 'check.py', 'check.sh', 'csc50.cmd',
    'finalize.py', 'prepare.py', 'inputs/CompilerHost.cs',
    'inputs/EvaluateProjects.cs', 'inputs/Generator.cs',
    'inputs/Microsoft.pubkey.hex', 'inputs/Probe.cs')]
output = root / 'compiler5-bootstrap-source-1.tar.gz'
with output.open('wb') as raw:
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w') as archive:
            for path in sorted(files):
                entry = archive.gettarinfo(str(path), 'compiler5-bootstrap/' + path.relative_to(root).as_posix())
                entry.mtime = entry.uid = entry.gid = 0
                entry.uname = entry.gname = ''
                entry.mode = 0o755 if path.suffix == '.sh' else 0o644
                with path.open('rb') as source:
                    archive.addfile(entry, source)
digest = hashlib.sha256(output.read_bytes()).hexdigest()
assert "'" + digest + "'" in (root / 'PKGBUILD').read_text(), digest
print(digest, output.name)
