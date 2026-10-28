"""Compare every published Core API, identity and neutral resource value."""
from pathlib import Path
import json
import sys

here,actual=(Path(p) for p in sys.argv[1:])
baseline=json.loads((here/'published-api.json').read_text())
count=0
for name,expected in baseline.items():
    result=json.loads((actual/'api'/(name+'.json')).read_text())
    assert result['identity']==expected['identity'],name
    assert result['api']==expected['api'],(name,set(expected['api'])-set(result['api']),set(result['api'])-set(expected['api']))
    count+=len(result['api'])
assert count==7845,count
expected={x['name']:x for x in json.loads((here/'published-metadata.json').read_text())}
metadata={x['name']:x for x in json.loads((actual/'metadata.json').read_text())}
assert set(metadata)==set(expected)
strings=sets=0
for name,wanted in expected.items():
    for field in ['name','version','public_key','public_key_token','attributes','resources']:
        assert metadata[name][field]==wanted[field],(name,field)
    sets+=len(wanted['resources']);strings+=sum(len(v) for v in wanted['resources'].values())
assert (sets,strings)==(13,807),(sets,strings)
print('PASS all7845 exact public/protected API declarations, eleven signing/version identities and807 strings in13 resource manifests')
