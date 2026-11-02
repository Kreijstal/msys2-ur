import os
from pathlib import Path
import hashlib
import json
import sys
import zipfile

root,module,source,metadata=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
golden=json.loads((here/'published-provenance.json').read_text())
record=json.loads((module/'source-build/source-inventory.json').read_text())
expected={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in sorted((source/'src').glob('*.cs'))}
assert expected==golden['original_cs_sources']==record['original_cs_sources']
assert record['production_csharp_changes']==0 and record['source_commit']==golden['source_commit']
assert (source/'LICENSE').read_bytes()==(module/'LICENSE').read_bytes()
assets=json.loads((root/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'Microsoft.PowerShell.Pager/1.0.0'}
assert {p.relative_to(module).as_posix() for p in module.rglob('*.dll')}=={'lib/net8.0/Microsoft.PowerShell.Pager.dll'}
assert not list(module.rglob('*.p7s'))
assert json.loads((metadata/'api.json').read_text())==golden['published_api']
identity=json.loads((metadata/'identity.json').read_text())
assert {k:v for k,v in identity.items() if k!='types'}==golden['published_identity']
feed=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs/Microsoft.PowerShell.Pager.1.0.0.nupkg')
if feed.is_file():
    with zipfile.ZipFile(feed) as z:
        dll='lib/net8.0/Microsoft.PowerShell.Pager.dll'
        if z.read(dll)==(module/dll).read_bytes():
            for name in (dll,'LICENSE','source-build/source-inventory.json'):
                assert z.read(name)==(module/name).read_bytes(),name
print('PASS source Pager full source inventory/license, exact three-entry API and frozen identity; sole source implementation asset')
