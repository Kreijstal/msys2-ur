"""Produce deterministic source inputs and verify the recipe's pinned checksum."""
from pathlib import Path
import gzip
import hashlib
import re
import sys
import tarfile

root = Path(__file__).resolve().parent
files = [root / name for name in ['README.md', 'build.py', 'check.py', 'pack.py', 'audit.py']]
files += [p for p in (root / 'inputs').iterdir() if p.is_file()]
output = root / 'netstandard-reference-source-3.tar.gz'
with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
    with tarfile.open(fileobj=gz, mode='w') as archive:
        for path in sorted(files):
            entry = archive.gettarinfo(str(path), 'netstandard-reference/' + path.relative_to(root).as_posix())
            entry.mtime = entry.uid = entry.gid = 0
            entry.uname = entry.gname = ''
            entry.mode = 0o644
            with path.open('rb') as source:
                archive.addfile(entry, source)
digest = hashlib.sha256(output.read_bytes()).hexdigest()
if sys.argv[1:] == ['--update-checksum']:
    recipe = root / 'PKGBUILD'
    text = recipe.read_text()
    matches = list(re.finditer(r"'[0-9a-f]{64}'", text))
    assert len(matches) == 3
    old = matches[1]
    recipe.write_text(text[:old.start()] + "'" + digest + "'" + text[old.end():])
else:
    assert not sys.argv[1:], 'usage: make-source.py [--update-checksum]'
assert "'" + digest + "'" in (root / 'PKGBUILD').read_text(), digest
print(digest, output.name)
