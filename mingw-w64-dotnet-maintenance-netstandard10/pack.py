"""Retain original Standard implementation metadata and newer-framework inbox groups."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();name=sys.argv[2];here=Path(__file__).resolve().parent
record=json.loads((out/'source-inputs.json').read_text())['projects'][name]
package=out/'feed'/(name+'.'+record['version']+'.nupkg')
publisher=here/'inputs'/(name+'.publisher.nuspec')
spec=E.parse(publisher).getroot();uri=spec.tag.partition('}')[0][1:];ns={'n':uri};E.register_namespace('',uri)
md=spec.find('n:metadata',ns);assert md.findtext('n:id',namespaces=ns)==name
assert md.findtext('n:version',namespaces=ns)==record['version']
repository=md.find('n:repository',ns);assert repository.get('commit')==record['commit']
dependencies=md.find('n:dependencies',ns);assert dependencies is not None
groups={}
for group in list(dependencies):
    target=group.get('targetFramework')
    if target.startswith('.NETFramework'):
        dependencies.remove(group);continue
    groups[target]={e.get('id'):dict(e.attrib) for e in group}
    if target!='.NETStandard2.0':assert len(group)==0,(name,target)
assert {n:v['version'] for n,v in groups['.NETStandard2.0'].items()}==record['dependencies']
assert len(groups)==3,groups
for item in list(md):
    if item.tag.rsplit('}',1)[-1] in {'icon','frameworkAssemblies'}:md.remove(item)
with zipfile.ZipFile(package) as z:
    entries={p:z.read(p) for p in z.namelist() if not p.endswith('.nuspec')}
entries[name+'.nuspec']=E.tostring(spec,encoding='utf-8',xml_declaration=True)
for target in groups:
    if target=='.NETStandard2.0':continue
    tfm=target.replace('.NETStandard','netstandard').replace('.NETCoreApp','netcoreapp')
    entries['lib/'+tfm+'/_._']=b''
assert entries['LICENSE'] and entries['PACKAGE.md']
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for path,data in sorted(entries.items()):
        info=zipfile.ZipInfo(path,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
        z.writestr(info,data)
(out/name/'package-metadata.json').write_text(json.dumps(dict(publisher_nuspec_sha256=hashlib.sha256(publisher.read_bytes()).hexdigest(),preserved_groups=groups,legacy_framework_assets_not_built=True,package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()),indent=2)+'\n')
print('PASS original Standard dependency metadata and two higher-framework inbox groups:',name)
