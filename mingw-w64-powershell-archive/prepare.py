"""Prepare pinned Archive source with the explicit fallback-resource correction."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

source, output = (Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
golden=json.loads((here/'published-source-provenance.json').read_text())
output.mkdir();module=output/'module';module.mkdir()
record=dict(source_commit=golden['source_commit'],source_archive_sha256=golden['source_archive_sha256'],
            published_source_comparison=golden,original_files={},packaged_files={})
for name,expected in golden['files'].items():
    path=source/'Microsoft.PowerShell.Archive'/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['source_sha256'],name
    target=module/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    record['original_files'][name]=expected['source_sha256']
psm=module/'Microsoft.PowerShell.Archive.psm1'
psm.write_text(psm.read_text(encoding='utf-8-sig').replace('\r\n','\n'))
patch=here/'0001-preserve-reserved-device-warning-in-fallback-data.patch'
subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=module,check=True)
for name in golden['files']:
    record['packaged_files'][name]=hashlib.sha256((module/name).read_bytes()).hexdigest()
record['patch_sha256']=hashlib.sha256(patch.read_bytes()).hexdigest()
record['change']='One fallback resource string added; source PSM1 BOM/line endings normalized; no compression/extraction algorithm changes.'
shutil.copyfile(source/'LICENSE',output/'LICENSE')
(output/'source-build.json').write_text(json.dumps(record,indent=2)+'\n')
