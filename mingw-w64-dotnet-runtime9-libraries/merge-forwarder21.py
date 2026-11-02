"""Merge the genuine original Standard2.1 forwarding target before dependent restores."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();name='Microsoft.Bcl.AsyncInterfaces'
record=json.loads((out/'source-inputs.json').read_text())['projects']['forwarder:'+name]
assert record['original_supported_framework']=='netstandard2.1' and not record['resolved_dependencies']
package=out/'feed'/(name+'.9.0.0.nupkg')
with zipfile.ZipFile(package) as z:entries={p:z.read(p) for p in z.namelist()}
spec_name=next(p for p in entries if p.endswith('.nuspec'));spec=E.fromstring(entries[spec_name]);uri=spec.tag.partition('}')[0][1:]
E.register_namespace('',uri);deps=spec.find('n:metadata/n:dependencies',{'n':uri});assert deps is not None
groups=[g for g in deps if g.get('targetFramework')=='.NETStandard2.1']
assert len(groups)<=1
for g in groups:deps.remove(g)
# The empty group prevents fallback to the Standard2.0 Tasks.Extensions dependency.
E.SubElement(deps,'{'+uri+'}group',targetFramework='.NETStandard2.1')
entries[spec_name]=E.tostring(spec,encoding='utf-8',xml_declaration=True)
target=out/'forwarder-netstandard21'/name/'bin/Release/netstandard2.1'/(name+'.dll')
entries['lib/netstandard2.1/'+name+'.dll']=target.read_bytes()
assert not any(p.startswith('lib/netstandard2.1/') and p!='lib/netstandard2.1/'+name+'.dll' for p in entries)
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for path,data in sorted(entries.items()):
        info=zipfile.ZipInfo(path,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
print('PASS original Standard2.1 forwarder and empty dependency group merged:',name)
