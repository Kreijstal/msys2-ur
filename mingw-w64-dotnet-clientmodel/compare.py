"""Require every published API declaration and all release identities unchanged."""
from pathlib import Path
import json,sys

here,out=(Path(p) for p in sys.argv[1:])
expected=json.loads((here/'published-api.json').read_text());actual=json.loads((out/'api.json').read_text())
assert actual['identity']==expected['identity']
missing=set(expected['api'])-set(actual['api']);extra=set(actual['api'])-set(expected['api'])
for label,values in [('MISSING',missing),('EXTRA',extra)]:
    for value in sorted(values):print(label,value)
assert not missing and not extra
expected=json.loads((here/'published-metadata.json').read_text())[0]
actual=json.loads((out/'metadata.json').read_text())[0]
for field in ['name','version','public_key','public_key_token','attributes','resources']:
    assert actual[field]==expected[field],field
print('PASS all'+str(len(json.loads((out/'api.json').read_text())['api']))+' exact published API declarations and release/signing identities')
