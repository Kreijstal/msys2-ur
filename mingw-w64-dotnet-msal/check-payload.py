"""Gate all five original-source runtime payloads and actual NuGet compiler assets."""
from pathlib import Path
import hashlib,json,sys,zipfile

mode,out=sys.argv[1],Path(sys.argv[2]);sha=lambda b:hashlib.sha256(b).hexdigest();hashes={}
for name,version in [('Microsoft.Identity.Client','4.61.3'),('Microsoft.Identity.Client.Extensions.Msal','4.61.3'),
                     ('Microsoft.IdentityModel.Abstractions','6.35.0'),('System.Text.Json','8.0.5'),('System.Security.Cryptography.ProtectedData','8.0.0')]:
    cache=out/'cache'/name.lower()/version
    with zipfile.ZipFile(cache/(name.lower()+'.'+version+'.nupkg')) as z:
        impl=z.read('lib/net8.0/'+name+'.dll');hashes[name]=sha(impl)
        compiler='lib/net8.0/'+name+'.dll' if name=='System.Security.Cryptography.ProtectedData' else 'ref/net8.0/'+name+'.dll'
        if name!='System.Security.Cryptography.ProtectedData':
            r=json.loads(z.read('source-build/inventory.json'))
            if name.startswith('Microsoft.Identity.Client'):
                assert r['source_commit']=='88df64013795d4e3716e1f677600f8164ffdb542';record=r['projects'][name]
            elif name=='System.Text.Json':record=r['projects']['Lib']
            else:record=r
            expected=record['source_outputs'][name+'.dll'] if name=='System.Text.Json' else record['implementation_sha256']
            assert sha(impl)==expected and sha(z.read(compiler))==record['reference_sha256']
        if mode=='verify':
            assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==impl
            assets=json.loads((out/'obj/project.assets.json').read_text())['targets']['net8.0'][name+'/'+version]
            assert set(assets['compile'])=={compiler} and set(assets['runtime'])=={'lib/net8.0/'+name+'.dll'}
if mode=='stage':(out/'source-runtime-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
else:
    assert json.loads((out/'source-runtime-sha256.json').read_text())==hashes
    print('PASS all five source runtime hashes and actual MSAL/cache/dependency compiler/runtime assets')
