"""Add the independently built original NET8 MEF target before dependent restores."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();name=sys.argv[2]
record=json.loads((out/'source-inputs.json').read_text())['projects']['baseline:'+name]
package=out/'feed'/(name+'.9.0.0.nupkg')
with zipfile.ZipFile(package) as z:entries={p:z.read(p) for p in z.namelist()}
spec_name=next(p for p in entries if p.endswith('.nuspec'));spec=E.fromstring(entries[spec_name]);uri=spec.tag.partition('}')[0][1:]
E.register_namespace('',uri);ns={'n':uri};md=spec.find('n:metadata',ns);deps=md.find('n:dependencies',ns)
assert deps is not None
for g in list(deps):
    if g.get('targetFramework')=='net8.0':deps.remove(g)
group=E.SubElement(deps,'{'+uri+'}group',targetFramework='net8.0')
for ident,version in record['resolved_dependencies'].items():E.SubElement(group,'{'+uri+'}dependency',id=ident,version='['+version+']',exclude='Build,Analyzers')
entries[spec_name]=E.tostring(spec,encoding='utf-8',xml_declaration=True)
folder=out/'baseline-net8'/name/'bin/Release/net8.0'
for p in folder.rglob('*.dll'):
    if p.name not in {name+'.dll',name+'.resources.dll'}:continue
    entries['lib/net8.0/'+p.relative_to(folder).as_posix()]=p.read_bytes()
assert 'lib/net8.0/'+name+'.dll' in entries
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for path,data in sorted(entries.items()):
        info=zipfile.ZipInfo(path,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
print('PASS original NET8 and Standard MEF source assets merged before dependent restore:',name)
