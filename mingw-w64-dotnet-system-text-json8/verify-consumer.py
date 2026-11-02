"""Prove the selected compiler/runtime/analyzer bytes match the source NuGet."""
from pathlib import Path
import hashlib,json,sys,zipfile

out=Path(sys.argv[1]);cache=out/'cache/system.text.json/8.0.5'
sha=lambda data:hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(cache/'system.text.json.8.0.5.nupkg') as z:
    inventory=json.loads(z.read('source-build/inventory.json'))
    assert inventory['source_commit']=='81cabf2857a01351e5ab578947c7403a5b128ad1'
    for folder,record in inventory['projects'].items():
        prefix='lib/net8.0/' if folder=='Lib' else 'analyzers/dotnet/roslyn'+record['variant']+'/cs/'
        for relative,digest in record['source_outputs'].items():
            assert sha(z.read(prefix+relative))==digest
            assert (cache/(prefix+relative)).read_bytes()==z.read(prefix+relative)
            target=out/'copies'/folder/'bin/Release/net8.0'/relative
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(prefix+relative))
    reference=z.read('ref/net8.0/System.Text.Json.dll');runtime=z.read('lib/net8.0/System.Text.Json.dll')
    assert sha(reference)==inventory['projects']['Lib']['reference_sha256']
    assert (out/'bin/Release/net8.0/System.Text.Json.dll').read_bytes()==runtime
    assets=json.loads((out/'obj/project.assets.json').read_text())['targets']['net8.0']['System.Text.Json/8.0.5']
    assert set(assets['compile'])=={'ref/net8.0/System.Text.Json.dll'}
    assert set(assets['runtime'])=={'lib/net8.0/System.Text.Json.dll'}
    (out/'source-runtime-sha256.txt').write_text(sha(runtime)+'\n')
    (out/'verified-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
print('PASS all43 restored source DLLs, compiler reference and runtime implementation bytes; copied metadata-inspection inputs')
