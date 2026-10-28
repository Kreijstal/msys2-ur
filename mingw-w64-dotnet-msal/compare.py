"""Require both complete published APIs, identities, signed headers and directives."""
from pathlib import Path
import json,sys

here,out=(Path(p) for p in sys.argv[1:])
for name,count in [('Microsoft.Identity.Client',1068),('Microsoft.Identity.Client.Extensions.Msal',69)]:
    gold=json.loads((here/(name+'.api.json')).read_text());actual=json.loads((out/(name+'.api.json')).read_text())
    assert len(gold['api'])==count and actual['identity']==gold['identity']
    missing=set(gold['api'])-set(actual['api']);extra=set(actual['api'])-set(gold['api'])
    for label,values in [('MISSING',missing),('EXTRA',extra)]:
        for value in sorted(values):print(label,value)
    assert not missing and not extra
    gold=json.loads((here/(name+'.metadata.json')).read_text())[0];actual=json.loads((out/(name+'.metadata.json')).read_text())[0]
    for key in ['name','version','public_key','public_key_token','attributes','resources','assembly_metadata','raw_resources']:
        assert actual[key]==gold[key],(name,key)
    assert actual['strong_name_signed'] and actual['strong_name_signature_nonzero']
    print('PASS',name,'all'+str(count)+' published APIs, exact release/signing metadata and original embedded resource bytes')
