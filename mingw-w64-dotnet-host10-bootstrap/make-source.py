"""Reproduce the pinned source-only native host build workflow."""
from pathlib import Path
import gzip,hashlib,tarfile
root=Path(__file__).resolve().parents[1];folder=root/'tests/runtime10-bootstrap'
names=['prepare-host.py','prepare-version.py','generate-host-resources.py','build-host.sh',
       'build-all-host.sh','audit-host.py','check-native-host.py','stage-host-package.py',
       'host-mingw.patch','inputs/CalculateAssemblyAndFileVersions.cs','inputs/Arcade-LICENSE.TXT']
archive=Path(__file__).resolve().parent/'dotnet-host10-source-1.tar.gz'
with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
    for name in sorted(names):
        path=folder/name;info=tar.gettarinfo(str(path),'host10/'+name)
        info.uid=info.gid=info.mtime=0;info.uname=info.gname='';info.mode=0o644
        with path.open('rb') as stream:tar.addfile(info,stream)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest in (archive.parent/'PKGBUILD').read_text(),('Workflow changed; review and freeze a new candidate',digest)
print(digest,archive)
