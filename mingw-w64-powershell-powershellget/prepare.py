"""Validate every pinned module/DSC source input and retain the original assembler."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

source, out = (Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
gold=json.loads((here/'published-provenance.json').read_text())
actual={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ['src/PowerShellGet','DSC'] for p in (source/directory).rglob('*') if p.is_file()}
assert actual==gold['source_files'], 'source module/DSC inventory mismatch'
assert hashlib.sha256((source/'tools/build.psm1').read_bytes()).hexdigest()==gold['original_build_module_sha256']
out.mkdir(); prepared=out/'source'; prepared.mkdir()
for directory in ['src/PowerShellGet','DSC/DscResources','DSC/Modules']:
    shutil.copytree(source/directory,prepared/directory)
(prepared/'tools').mkdir()
shutil.copyfile(source/'tools/build.psm1',prepared/'tools/build.psm1')
shutil.copyfile(source/'LICENSE',out/'LICENSE')
(out/'source-build.json').write_text(json.dumps(dict(
    source_commit=gold['source_commit'],source_archive_sha256=gold['source_archive_sha256'],
    original_files=actual,original_build_module_sha256=gold['original_build_module_sha256'],
    source_changes=[],assembly_function='unchanged New-ModulePSMFile',
    note='Original module assembler only; upstream dependency/bootstrap/publish tasks are not invoked.'),indent=2)+'\n')
print('PASS complete original source inventory and assembler:',len(actual),'files')
