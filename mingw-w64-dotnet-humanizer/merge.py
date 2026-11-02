"""Combine independently compiled Standard2.0 and retained NET8-port NuGet assets."""
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile

out=Path(sys.argv[1]).resolve();filename='Humanizer.Core.2.14.1.nupkg'
def read(path):
    with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
entries=read(out/'packages/netstandard2.0'/filename)
other=read(out/'packages/net8.0'/filename)
spec_name=next(n for n in entries if n.endswith('.nuspec'))
spec=E.fromstring(entries[spec_name]);second=E.fromstring(other[spec_name]);uri=spec.tag.partition('}')[0][1:]
ns={'n':uri};E.register_namespace('',uri)
for root in [spec,second]:
    assert root.findtext('n:metadata/n:id',namespaces=ns)=='Humanizer.Core'
    assert root.findtext('n:metadata/n:version',namespaces=ns)=='2.14.1'
    assert root.find('n:metadata/n:repository',ns).get('commit')=='3ebc38de585fc641a04b0e78ed69468453b0f8a1'
deps=spec.find('n:metadata/n:dependencies',ns);groups=second.findall('n:metadata/n:dependencies/n:group',ns)
assert deps is not None and len(groups)==1 and groups[0].get('targetFramework')=='net8.0' and len(groups[0])==0
assert len(deps)==1 and deps[0].get('targetFramework')=='.NETStandard2.0' and len(deps[0])==0
deps.append(groups[0]);entries[spec_name]=E.tostring(spec,encoding='utf-8',xml_declaration=True)
for name,data in other.items():
    if name.startswith('lib/net8.0/'):entries[name]=data
for name in ['LICENSE','LICENSE.Bytes','LICENSE.Inflections']:
    assert entries[name]==other[name]
assert all('lib/'+tfm+'/Humanizer.dll' in entries for tfm in ['netstandard2.0','net8.0'])
with zipfile.ZipFile(out/'feed'/filename,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(entries.items()):
        info=zipfile.ZipInfo(name,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
print('PASS genuine Standard2.0 and retained NET8-port assets merged in Humanizer.Core2.14.1')
