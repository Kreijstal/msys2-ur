"""Require the exact restored source assets and dependency-free module identity."""
import os
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile

root,module,source=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
assets=json.loads((root/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'Microsoft.PowerShell.Archive/1.2.6'}
record=json.loads((module/'source-build/provenance.json').read_text())
expected={'Microsoft.PowerShell.Archive.psd1','Microsoft.PowerShell.Archive.psm1','en-US/ArchiveResources.psd1'}
assert set(record['packaged_files'])==expected
golden=json.loads((here/'published-source-provenance.json').read_text())
assert record['source_commit']==golden['source_commit']
assert record['source_archive_sha256']==golden['source_archive_sha256']
assert record['original_files']=={name:item['source_sha256'] for name,item in golden['files'].items()}
patch=here/'0001-preserve-reserved-device-warning-in-fallback-data.patch'
assert record['patch_sha256']==hashlib.sha256(patch.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as temp:
    original=source/'Microsoft.PowerShell.Archive'
    for name,item in golden['files'].items():
        data=(original/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['source_sha256'],name
        target=Path(temp)/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    psm=Path(temp)/'Microsoft.PowerShell.Archive.psm1'
    psm.write_text(psm.read_text(encoding='utf-8-sig').replace('\r\n','\n'))
    subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=temp,check=True,stdout=subprocess.PIPE)
    for name in expected:assert (module/name).read_bytes()==(Path(temp)/name).read_bytes(),name
for name,digest in record['packaged_files'].items():
    data=(module/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest,name
    assert b'# SIG # Begin signature block' not in data,name
assert not list(module.rglob('*.dll'))
installed=Path(os.environ['MINGW_PREFIX']+'/lib/powershell/Modules/Microsoft.PowerShell.Archive/1.2.6')
feed=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs/microsoft.powershell.archive.1.2.6.nupkg')
if feed.is_file():
    with zipfile.ZipFile(feed) as z:
        # Build-time checks may restore a newer candidate. Only compare loose
        # installed module bytes when this is exactly the installed package.
        same=all(z.read(name)==(module/name).read_bytes() for name in expected)
    if same:
        for name in expected:assert (installed/name).read_bytes()==(module/name).read_bytes(),name
        print('PASS restored installed NuGet source bytes equal installed loose module bytes')
print('PASS exact dependency-free source PSModule assets, hashes and absence of vendor signatures/binaries')
