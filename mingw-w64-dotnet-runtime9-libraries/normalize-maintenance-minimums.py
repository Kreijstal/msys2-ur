"""Keep exact producer refs while packaging compatible maintenance minimums."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile

out=Path(sys.argv[1]).resolve();name=sys.argv[2]
package=out/'feed'/(name+'.9.0.0.nupkg')
manifest=json.loads((out/'source-inputs.json').read_text())
record=manifest['projects'][name]
maintenance=set(json.loads(Path('/clang64/share/doc/dotnet-maintenance-netstandard/source-inputs.json').read_text())['projects'])
with zipfile.ZipFile(package) as z:
 entries={n:z.read(n) for n in z.namelist()}
specname=next(n for n in entries if n.endswith('.nuspec'))
tree=E.fromstring(entries[specname]);namespace=tree.tag.partition('}')[0][1:]
E.register_namespace('',namespace)
changes=[]
for dep in tree.iter():
 if not dep.tag.endswith('dependency') or dep.get('id') not in maintenance:continue
 ident=dep.get('id');version=record['resolved_dependencies'][ident]
 assert dep.get('version') in {version,'['+version+']'},(name,dep.attrib)
 if dep.get('version')!=version:
  changes.append(dict(id=ident,before=dep.get('version'),after=version,
   original_source_minimum=record['original_package_minimums'].get(ident),
   producer_exact_reference_version=version))
  dep.set('version',version)
original_payload={n:hashlib.sha256(data).hexdigest() for n,data in entries.items() if n!=specname}
entries[specname]=E.tostring(tree,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in sorted(entries.items()):
  info=zipfile.ZipInfo(n,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
  z.writestr(info,data)
with zipfile.ZipFile(package) as z:
 assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n!=specname}==original_payload
folder=out/'dependency-policy';folder.mkdir(exist_ok=True)
(folder/(name+'.json')).write_text(json.dumps(dict(package=package.name,changes=changes,
 all_non_nuspec_payload_bytes_unchanged=True,non_nuspec_payload_sha256=original_payload,
 producer_compilation_references_remain_exact=True),indent=2)+'\n')
print('PASS maintenance package minimums:',name,len(changes),'metadata entries; all binary/resource/doc bytes unchanged')
