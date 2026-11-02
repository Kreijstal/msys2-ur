"""Validate restored module inventory, source provenance and exact source provider bytes."""
import os
from pathlib import Path
import hashlib
import json
import sys
import zipfile

out,module=(Path(p).resolve() for p in sys.argv[1:])
record=json.loads((module/'source-build/provenance.json').read_text())
here=Path(__file__).resolve().parent
gold=json.loads((here/'published-provenance.json').read_text())
assert record['source_commit']==gold['source_commit']
assert record['original_files']==gold['source_files']
assert set(record['module_files'])==set(gold['module_assets'])
for name,expected in record['module_files'].items():
    assert hashlib.sha256((module/name).read_bytes()).hexdigest()==expected,name
assert not list(module.rglob('*.dll')), 'unexpected PowerShellGet DLL'
dependency=out/'empty-packages/packagemanagement/1.4.8.1'
with zipfile.ZipFile(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs/packagemanagement.1.4.8.1.nupkg') as z:
    for name in z.namelist():
        if name.endswith('.dll'): assert (dependency/name).read_bytes()==z.read(name),name
print('PASS fresh PowerShellGet restore: all16 module assets and installed source PackageManagement implementation bytes')
