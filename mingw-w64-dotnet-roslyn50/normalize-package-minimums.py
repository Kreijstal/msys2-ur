"""Preserve exact compiler inputs and package runtime dependency minimums."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile

out=Path(sys.argv[1]).resolve();assembly=sys.argv[2]
name='Microsoft.CodeAnalysis.Common' if assembly=='Microsoft.CodeAnalysis' else assembly
package=out/'feed'/(name+'.5.0.0.nupkg')
record=json.loads((out/'source-inputs.json').read_text())['projects'][assembly]
with zipfile.ZipFile(package) as z:entries={n:z.read(n) for n in z.namelist()}
specname=next(n for n in entries if n.endswith('.nuspec'));tree=E.fromstring(entries[specname])
E.register_namespace('',tree.tag.partition('}')[0][1:]);changes=[]
for dep in tree.iter():
 if not dep.tag.endswith('dependency'):continue
 ident=dep.get('id');version=record['resolved_dependencies'][ident]
 assert dep.get('version') in {version,'['+version+']'},dep.attrib
 if ident=='Microsoft.CodeAnalysis.Common':
  assert dep.get('version')=='[5.0.0]';continue
 changes.append(dict(id=ident,before=dep.get('version'),after=version,
  original_minimum=record['original_package_minimums'][ident],producer_version=version))
 dep.set('version',version)
payload={n:hashlib.sha256(data).hexdigest() for n,data in entries.items() if n!=specname}
entries[specname]=E.tostring(tree,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in sorted(entries.items()):
  item=zipfile.ZipInfo(n,date_time=(2000,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o644<<16;z.writestr(item,data)
with zipfile.ZipFile(package) as z:assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n!=specname}==payload
folder=out/'dependency-policy';folder.mkdir(exist_ok=True)
(folder/(assembly+'.json')).write_text(json.dumps(dict(changes=changes,
 paired_common_version_remains_exact=True,all_non_nuspec_bytes_unchanged=True,
 non_nuspec_payload_sha256=payload),indent=2)+'\n')
print('PASS original-style runtime dependency minimums and exact paired Common:',name)
