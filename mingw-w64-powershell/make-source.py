"""Run from any directory to reproduce the recipe's source-only workflow archive."""
from pathlib import Path
import gzip
import hashlib
import sys
import tarfile

root=Path(__file__).resolve().parent.parent
# Workflow sources live in https://github.com/Kreijstal/dotnet-mingw-bootstrap
# (workflows/); pass its checkout, default ../../dotnet-mingw-bootstrap. The
# archive keeps their former tests/ member names so its bytes stay the same.
bootstrap=Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/'dotnet-mingw-bootstrap'
full=['prepare.py','localaccounts-overlay.py','build.sh','build-desktop.sh','build-package.sh',
      'audit-source.py','audit-catalog.py','audit-native-console.py','check-localaccounts-api.sh',
      'CheckLocalAccountsApi.cs','stage.py','audit-payload.py','audit-graphical-source.py',
      'InspectGraphicalAssets.cs','collect-package-licenses.py','stage-package.py','Smoke.ps1',
      'CimWmiSmoke.ps1','WmiStaProbe.ps1','GallerySmoke.ps1','ChildSmoke.ps1','DesktopSmoke.ps1']
files=[Path('tests/powershell-full-sdk')/name for name in full]
files.extend([Path('tests/powershell-core/prepare.py'),
              Path('mingw-w64-powershell-module-test-host/audit-source.py')])
files.extend(Path('mingw-w64-powershell')/name for name in
             ['launcher.c','LICENSE.launcher','README.md','check-package.sh',
              'check-launcher.py','source-dependency-lock.json'])
archive=root/'mingw-w64-powershell/powershell-source-workflow-4.tar.gz'
with archive.open('wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
    with tarfile.open(fileobj=gz,mode='w') as tar:
        for relative in sorted(files):
            path=(bootstrap/'workflows'/relative.relative_to('tests') if relative.parts[0]=='tests'
                  else root/relative)
            info=tar.gettarinfo(str(path),'workflow/'+relative.as_posix())
            info.uid=info.gid=info.mtime=0
            info.uname=info.gname=''
            info.mode=0o644
            with path.open('rb') as stream:
                tar.addfile(info,stream)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest in (root/'mingw-w64-powershell/PKGBUILD').read_text(), (
    'Workflow differs from the frozen recipe; review changes and create a new candidate',digest)
print(digest,archive)
