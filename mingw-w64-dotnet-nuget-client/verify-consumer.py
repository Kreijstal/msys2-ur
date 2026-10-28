"""Prove compile/runtime bytes came from the source NuGet payloads just restored."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

here,out=(Path(p) for p in sys.argv[1:])
libraries=json.loads((here/'libraries.json').read_text())
assets=json.loads((out/'obj/project.assets.json').read_text())
target=assets['targets']['net8.0']
sha=lambda data:hashlib.sha256(data).hexdigest()
for name in libraries:
    folder=out/'cache'/name.lower()/'6.9.1'
    with zipfile.ZipFile(folder/(name.lower()+'.6.9.1.nupkg')) as z:
        inventory=json.loads(z.read('source-build/inventory.json'))
        assert inventory['project']==name and inventory['source_commit']=='623fde83a3cd73cb479ec7fa03866c6116894dbf'
        runtime=z.read('lib/net8.0/'+name+'.dll');reference=z.read('ref/net8.0/'+name+'.dll')
        assert sha(runtime)==inventory['implementation_sha256']
        assert sha(reference)==inventory['reference_sha256']
        assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==runtime,name
        assert set(target[name+'/6.9.1']['compile'])=={'ref/net8.0/'+name+'.dll'},name
        assert set(target[name+'/6.9.1']['runtime'])=={'lib/net8.0/'+name+'.dll'},name
        assert (folder/'ref/net8.0'/(name+'.dll')).read_bytes()==reference,name
print('PASS all eleven compiler reference and runtime implementations exactly match their source package inventories')
