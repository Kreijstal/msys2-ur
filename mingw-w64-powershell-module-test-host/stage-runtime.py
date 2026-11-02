"""Stage original module manifests and source-built Add-Type reference metadata."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

source, output, references = (Path(p).resolve() for p in sys.argv[1:])
record = {'manifests': {}, 'autoload_manifests': {}, 'reference_metadata': {}}
for name in ('Microsoft.PowerShell.Security','Microsoft.PowerShell.Management','Microsoft.PowerShell.Utility','CimCmdlets'):
    folder = source/'src/Modules/Windows'/name
    module = output/'Modules'/name
    module.mkdir(parents=True,exist_ok=True)
    for path in sorted(folder.iterdir()):
        assert path.suffix in ('.psd1','.ps1xml'),path
        shutil.copyfile(path,output/path.name)
        shutil.copyfile(path,module/path.name)
        record['manifests'][path.relative_to(source).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        record['autoload_manifests'][(module/path.name).relative_to(output).as_posix()] = path.relative_to(source).as_posix()
(output/'ref').mkdir(exist_ok=True)
for path in sorted(references.glob('*.dll')):
    shutil.copyfile(path,output/'ref'/path.name)
    record['reference_metadata'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
assert len(record['reference_metadata']) > 100
(output/'source-runtime-metadata.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged original module manifests and',len(record['reference_metadata']),'source reference assemblies')
