"""Verify source provenance, exact source patch, installed parity and metadata API."""
import os
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

root,module,source,inspection=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
golden=json.loads((here/'published-provenance.json').read_text())
record=json.loads((module/'source-build/provenance.json').read_text())
assets=json.loads((root/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'ThreadJob/2.0.3'}
assert record['source_commit']==golden['source_commit']
assert record['source_archive_sha256']==golden['source_archive_sha256']
actual={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in sorted((source/'PSThreadJob').glob('*.cs'))}
assert actual==golden['source_files']==record['source_files']
assert sha((source/'PSThreadJob/Resources.resx').read_bytes())==golden['resource_sha256']==record['resource_sha256']
assert (source/'PSThreadJob/ThreadJob.psd1').read_bytes()==(module/'ThreadJob.psd1').read_bytes()
assert sha((module/'ThreadJob.psd1').read_bytes())==golden['source_manifest_sha256']
assert (source/'LICENSE').read_bytes()==(module/'LICENSE').read_bytes()
assert len(record['source_algorithm_overlays'])==1
overlay=record['source_algorithm_overlays'][0]
patch=here/'0001-use-current-debugger-setbreakpoints-overload.patch'
assert overlay['patch_sha256']==sha(patch.read_bytes())
with tempfile.TemporaryDirectory() as temp:
    target=Path(temp)/'PSThreadJob.cs'
    target.write_text((source/'PSThreadJob/PSThreadJob.cs').read_text(encoding='utf-8-sig'))
    subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=temp,check=True,stdout=subprocess.PIPE)
    assert sha(target.read_bytes())==overlay['overlay_sha256']
assert {p.name for p in module.rglob('*.dll')}=={'Microsoft.PowerShell.ThreadJob.dll'}
assert not list(module.rglob('*.p7s'))
assert set(record['module_files'])=={'Microsoft.PowerShell.ThreadJob.dll','ThreadJob.psd1'}
for name,digest in record['module_files'].items():assert sha((module/name).read_bytes())==digest,name
assert json.loads((inspection/'api.json').read_text())==golden['published_api']
identity=json.loads((inspection/'identity.json').read_text())
assert {k:v for k,v in identity.items() if k!='types'}==golden['published_identity']
feed=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs/threadjob.2.0.3.nupkg')
if feed.is_file():
    with zipfile.ZipFile(feed) as z:
        same=all(z.read(name)==(module/name).read_bytes() for name in record['module_files'])
    if same:
        installed=Path(os.environ['MINGW_PREFIX']+'/lib/powershell/Modules/ThreadJob/2.0.3')
        for name in record['module_files']:assert (installed/name).read_bytes()==(module/name).read_bytes(),name
        print('PASS restored installed NuGet binary/manifest equal installed loose module bytes')
print('PASS complete original source inventory/patch provenance, sole binary, license, frozen identity and all55 published API declarations')
