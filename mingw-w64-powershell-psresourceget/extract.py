"""Verify and extract the entire pinned source archive without archive links."""
from pathlib import Path
import hashlib, shutil, sys, tarfile

archive, out = (Path(p) for p in sys.argv[1:])
with archive.open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == '4819dc0283c6a28979aa5a26aa70ad41468de1a2a52e0729a61062086c08bc03'
out.mkdir()
with tarfile.open(archive, 'r|gz') as t:
    for member in t:
        if member.isdir(): continue
        assert member.isfile(), member.name
        prefix, path = member.name.split('/', 1)
        assert prefix == 'PSResourceGet-44697aed1740126153a8d9dd0ef368261b2fe45c'
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        target = out/path
        target.parent.mkdir(parents=True, exist_ok=True)
        with t.extractfile(member) as source, target.open('wb') as dest:
            shutil.copyfileobj(source, dest)
print('PASS complete pinned PSResourceGet source archive hash and extraction')
