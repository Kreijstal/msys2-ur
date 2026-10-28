"""Extract the pinned complete production/build tree under a short Windows path."""
from pathlib import Path, PurePosixPath
import hashlib
import shutil
import sys
import tarfile

archive,out=(Path(p) for p in sys.argv[1:])
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='15861d82692e0e7d904f7267cbc3efd35a14d37b941c8cee2bb4fb39972a1f23'
out.mkdir()
count=0
with tarfile.open(archive,'r:gz') as tar:
    for member in tar:
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='NuGet.Client-623fde83a3cd73cb479ec7fa03866c6116894dbf'
        relative=PurePosixPath(*parts[1:])
        assert '..' not in relative.parts and not relative.is_absolute()
        # Test fixture paths exceed MAX_PATH; no test/docs file is an input to
        # these original production projects. Keep all other source/build files.
        if not relative.parts or relative.parts[0] in ['test','docs','.github']:
            continue
        target=out/str(relative)
        if member.isdir():target.mkdir(parents=True,exist_ok=True)
        else:
            assert member.isfile(),member.name
            target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
            count+=1
print('PASS pinned NuGet archive; extracted complete production/build tree:',count,'files')
