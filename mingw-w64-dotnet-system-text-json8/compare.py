"""Compare the complete .NET8 JSON/generator API and neutral/localized metadata."""
from pathlib import Path
import json,re,sys
import xml.etree.ElementTree as E

here,actual=(Path(p) for p in sys.argv[1:])
api=json.loads((here/'published-api.json').read_text());count=0
for name,expected in api.items():
    got=json.loads((actual/'api'/(name+'.json')).read_text())
    assert got['identity']==expected['identity'],(name,'identity')
    missing=set(expected['api'])-set(got['api']);extra=set(got['api'])-set(expected['api'])
    for label,values in [('MISSING',missing),('EXTRA',extra)]:
        for value in sorted(values):print(name,label,value)
    assert not missing and not extra,(name,len(missing),len(extra))
    count+=len(got['api'])
assert count==1784,count
expected={}
for record in json.loads((here/'published-metadata.json').read_text()):
    path=record['file'].replace('\\','/').split('/metadata-only/')[1]
    if path.startswith('lib/net8.0/'):key='Lib/'+path.split('/')[-1]
    else:
        match=re.fullmatch(r'analyzers/dotnet/roslyn(3\.11|4\.0|4\.4)/cs/(.*)',path)
        assert match,path
        key='Gen'+match[1]+'/'+match[2]
    expected[key]=record
got={}
for record in json.loads((actual/'metadata.json').read_text()):
    prefix,relative=record['file'].replace('\\','/').rsplit('/bin/Release/net8.0/',1)
    got[prefix.rsplit('/',1)[1]+'/'+relative]=record
assert set(got)==set(expected),(set(expected)-set(got),set(got)-set(expected))
entries=sets=0
for name,wanted in expected.items():
    for field in ['name','version','public_key','public_key_token','attributes','resources']:
        assert wanted[field]==got[name][field],(name,field)
    def canonical(node):
        return (node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),tuple(canonical(c) for c in node))
    assert set(wanted['embedded_xml'])==set(got[name]['embedded_xml']),(name,'embedded XML names')
    for resource,xml in wanted['embedded_xml'].items():
        assert canonical(E.fromstring(xml))==canonical(E.fromstring(got[name]['embedded_xml'][resource])),(name,resource)
    sets+=len(wanted['resources']);entries+=sum(len(v) for v in wanted['resources'].values())
assert (sets,entries)==(43,1460),(sets,entries)
print('PASS all1784 published API declarations,43 assembly identities/resource sets and1460 neutral/localized strings')
