"""Require source package implementation/reference bytes and actual asset selection."""
from pathlib import Path
import hashlib,json,sys,zipfile

mode,out=sys.argv[1],Path(sys.argv[2]);name='System.Memory.Data';cache=out/'cache/system.memory.data/1.0.2'
sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(cache/'system.memory.data.1.0.2.nupkg') as z:
    r=json.loads(z.read('source-build/inventory.json'));assert r['source_commit']=='7e3cf643977591e9041f4c628fd4d28237398e0b'
    impl=z.read('lib/net8.0/'+name+'.dll');ref=z.read('ref/net8.0/'+name+'.dll')
    assert sha(impl)==r['implementation_sha256'] and sha(ref)==r['reference_sha256']
    if mode=='stage':(out/'source-runtime-sha256.txt').write_text(sha(impl)+'\n')
    else:
        assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==impl
        assets=json.loads((out/'obj/project.assets.json').read_text())['targets']['net8.0'][name+'/1.0.2']
        assert set(assets['compile'])=={'ref/net8.0/'+name+'.dll'} and set(assets['runtime'])=={'lib/net8.0/'+name+'.dll'}
        assert (cache/'ref/net8.0'/(name+'.dll')).read_bytes()==ref
        print('PASS exact source BinaryData runtime/reference payload and actual compiler/runtime asset selection')
