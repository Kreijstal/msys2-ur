"""Stage original Pester4 Core scripts with the rebuilt Gherkin implementation."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

source, output, gherkin = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir(parents=True)
record = {}
for name in ('Pester.psd1','Pester.psm1','Functions','Dependencies','en-US','lib','LICENSE'):
    path=source/name
    files=sorted(path.rglob('*')) if path.is_dir() else [path]
    for item in files:
        if not item.is_file() or item.suffix.lower() in ('.dll','.exe','.pdb','.nupkg'):continue
        relative=item.relative_to(source)
        target=output/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(item,target)
        record[relative.as_posix()]=hashlib.sha256(item.read_bytes()).hexdigest()
target=output/'lib/Gherkin/core/Gherkin.dll'
target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(gherkin,target)
(output/'source-pester-inventory.json').write_text(json.dumps(dict(
    source_commit='add7dc5f435287aa14db39c31f90159572e6a6df',original_source_files=record,
    source_gherkin_commit='55ab34d45dcd8249349704335c2aa2f90839fae3',
    rebuilt_gherkin_sha256=hashlib.sha256(gherkin.read_bytes()).hexdigest(),
    legacy_framework_binaries_included=False),indent=2)+'\n')
assert list(output.rglob('*.dll')) == [target]
print('Staged',len(record),'original Pester Core source/data files and source-built Gherkin; no vendor implementation binaries')
