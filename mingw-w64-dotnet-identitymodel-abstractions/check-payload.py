"""Stage original test fixtures and prove exact source NuGet compiler/runtime bytes."""
from pathlib import Path
import hashlib,json,sys,zipfile

mode,out=sys.argv[1],Path(sys.argv[2]);name='Microsoft.IdentityModel.Abstractions'
cache=out/'cache/microsoft.identitymodel.abstractions/6.35.0';sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(cache/'microsoft.identitymodel.abstractions.6.35.0.nupkg') as z:
    r=json.loads(z.read('source-build/inventory.json'))
    assert r['source_commit']=='c94c7fc235501d478221e979062bd8837a55575b'
    fixture=z.read('source-build/UpstreamTests.cs');assert sha(fixture)==r['adapted_test_sha256']
    impl=z.read('lib/net8.0/'+name+'.dll');ref=z.read('ref/net8.0/'+name+'.dll')
    assert sha(impl)==r['implementation_sha256'] and sha(ref)==r['reference_sha256']
    if mode=='stage':
        (out/'UpstreamTests.cs').write_bytes(fixture);(out/'source-runtime-sha256.txt').write_text(sha(impl)+'\n')
    else:
        assert (out/'UpstreamTests.cs').read_bytes()==fixture
        assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==impl
        assets=json.loads((out/'obj/project.assets.json').read_text())['targets']['net8.0'][name+'/6.35.0']
        assert set(assets['compile'])=={'ref/net8.0/'+name+'.dll'}
        assert set(assets['runtime'])=={'lib/net8.0/'+name+'.dll'}
        assert (cache/'ref/net8.0'/(name+'.dll')).read_bytes()==ref
        print('PASS source package test fixture/reference/runtime hashes and actual compiler/runtime asset selection')
