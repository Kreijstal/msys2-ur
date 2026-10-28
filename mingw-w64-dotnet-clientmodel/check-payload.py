"""Gate all three restored source implementations and ClientModel reference selection."""
from pathlib import Path
import hashlib,json,sys,zipfile

mode,out=sys.argv[1],Path(sys.argv[2]);sha=lambda b:hashlib.sha256(b).hexdigest();hashes={}
for name,version,commit in [('System.ClientModel','1.0.0','8ffa7d7f26bb2c5e3dadf74b2aa9c9ba9c9d9208'),
                            ('System.Memory.Data','1.0.2','7e3cf643977591e9041f4c628fd4d28237398e0b'),
                            ('System.Text.Json','8.0.5','81cabf2857a01351e5ab578947c7403a5b128ad1')]:
    cache=out/'cache'/name.lower()/version
    with zipfile.ZipFile(cache/(name.lower()+'.'+version+'.nupkg')) as package:
        inventory=json.loads(package.read('source-build/inventory.json'));assert inventory['source_commit']==commit
        impl=package.read('lib/net8.0/'+name+'.dll');ref=package.read('ref/net8.0/'+name+'.dll')
        record=inventory['projects']['Lib'] if name=='System.Text.Json' else inventory
        expected=record['source_outputs'][name+'.dll'] if name=='System.Text.Json' else record['implementation_sha256']
        assert sha(impl)==expected and sha(ref)==record['reference_sha256']
        hashes[name]=sha(impl)
        if mode=='verify':
            assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==impl
            assets=json.loads((out/'obj/project.assets.json').read_text())['targets']['net8.0'][name+'/'+version]
            assert set(assets['compile'])=={'ref/net8.0/'+name+'.dll'} and set(assets['runtime'])=={'lib/net8.0/'+name+'.dll'}
            assert (cache/'ref/net8.0'/(name+'.dll')).read_bytes()==ref
if mode=='stage':(out/'source-runtime-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
else:
    assert json.loads((out/'source-runtime-sha256.json').read_text())==hashes
    print('PASS all three source implementation/reference hashes and actual compiler/runtime asset selection')
