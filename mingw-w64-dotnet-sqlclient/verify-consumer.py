"""Check a fresh PackageReference's actual compile/runtime selections and payload bytes."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
out=Path(sys.argv[1]).resolve();sha=lambda b:hashlib.sha256(b).hexdigest()
package=out/'cache/system.data.sqlclient/4.9.1';nupkg=package/'system.data.sqlclient.4.9.1.nupkg'
with zipfile.ZipFile(nupkg) as z:
    expected=json.loads(z.read('source-build/expected-assets.json'))
    assert expected['experimental'] and not expected['full_runtime_compatibility_verified']
    for asset in ['lib/net8.0/System.Data.SqlClient.dll','ref/net8.0/System.Data.SqlClient.dll','runtimes/win/lib/net8.0/System.Data.SqlClient.dll']:
        assert (package/asset).read_bytes()==z.read(asset),asset
    assert sha(z.read('runtimes/win/lib/net8.0/System.Data.SqlClient.dll'))==expected['implementation_sha256']
    assert sha(z.read('ref/net8.0/System.Data.SqlClient.dll'))==expected['reference_sha256']
    (out/'expected-assets.json').write_bytes(z.read('source-build/expected-assets.json'))
    for project in ['protocol','values','assets']:
        root=out/project;assets=json.loads((root/'obj/project.assets.json').read_text());targets=assets['targets'];assert len(targets)==1
        selected=next(iter(targets.values()))['System.Data.SqlClient/4.9.1']
        assert list(selected['compile'])==['ref/net8.0/System.Data.SqlClient.dll']
        assert list(selected['runtime'])==['lib/net8.0/System.Data.SqlClient.dll']
        assert list(selected['runtimeTargets'])==['runtimes/win/lib/net8.0/System.Data.SqlClient.dll']
        result=root/'bin/Release/net8.0-windows';runtime=result/'runtimes/win/lib/net8.0/System.Data.SqlClient.dll'
        assert runtime.read_bytes()==z.read('runtimes/win/lib/net8.0/System.Data.SqlClient.dll')
        assert (result/'System.Data.SqlClient.dll').read_bytes()==z.read('lib/net8.0/System.Data.SqlClient.dll')
    if len(sys.argv)>2:
        feed=Path(sys.argv[2]);matches=[p for p in feed.glob('*.nupkg') if p.name.lower()==nupkg.name.lower()];assert len(matches)==1
        assert matches[0].read_bytes()==nupkg.read_bytes()
print('PASS fresh source-only NuGet package, exact reference/generic/Windows runtime asset selections and all consumer payload bytes')
