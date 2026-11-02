"""Verify complete source provenance, module assets, API/resources and Core forwarders."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as E
import zipfile

root,module,source,metadata=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
golden=json.loads((here/'published-provenance.json').read_text())
record=json.loads((module/'source-build/provenance.json').read_text())
assets=json.loads((root/'obj/project.assets.json').read_text())
assert set(assets['libraries'])=={'PSReadLine/2.3.6'}
assert record['source_commit']==golden['source_commit']
assert record['source_archive_sha256']==golden['source_archive_sha256']
assert record['production_csharp_changes']==0
for folder,key,count in [('PSReadLine','original_cs_sources',48),('Polyfill','original_polyfill_cs_sources',1)]:
    actual={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in sorted((source/folder).glob('*.cs'))}
    assert len(actual)==count and actual==golden[key]==record[key]
assert sha((source/'PSReadLine/PSReadLineResources.resx').read_bytes())==golden['resource_sha256']==record['resource_sha256']
assert record['original_module_assets']==golden['original_module_assets']
for name,digest in golden['original_module_assets'].items():
    assert sha((source/name).read_bytes())==digest
    assert (source/name).read_bytes()==(module/Path(name).name).read_bytes(),name
expected={Path(name).name for name in golden['original_module_assets']}|{
    'Microsoft.PowerShell.PSReadLine2.dll','Microsoft.PowerShell.Pager.dll','net6plus/Microsoft.PowerShell.PSReadLine.Polyfiller.dll'}
assert set(record['module_files'])==expected and len(expected)==9
for name,digest in record['module_files'].items():assert sha((module/name).read_bytes())==digest,name
assert {p.relative_to(module).as_posix() for p in module.rglob('*.dll')}=={p for p in expected if p.endswith('.dll')}
assert not list(module.rglob('*.p7s'))
assert json.loads((metadata/'api.json').read_text())==golden['published_api']
fields=('name','version','public_key_token','attributes')
identity=json.loads((metadata/'identity-main.json').read_text())
assert {k:identity[k] for k in fields}==golden['published_identity']
forwarders=json.loads((metadata/'identity-forwarders.json').read_text())
assert {k:forwarders[k] for k in fields}=={k:golden['published_forwarder_identity'][k] for k in fields}
assert set(forwarders['types'])=={'.<Module>'},'Core forwarder assembly must not supply legacy prediction implementations'
expected_types=golden['published_forwarder_identity']['exported_types']
actual_types=forwarders['exported_types']
assert len(actual_types)==5
assert [{k:v for k,v in item.items() if k!='target_version'} for item in actual_types]==[{k:v for k,v in item.items() if k!='target_version'} for item in expected_types]
assert all(item['target_version']=='7.4.6.500' for item in actual_types)
pager=Path('/clang64/lib/dotnet/library-packs/Microsoft.PowerShell.Pager.1.0.0.nupkg')
with zipfile.ZipFile(pager) as z:assert z.read('lib/net8.0/Microsoft.PowerShell.Pager.dll')==(module/'Microsoft.PowerShell.Pager.dll').read_bytes()
resources={p.get('name'):p.findtext('value') for p in E.parse(source/'PSReadLine/PSReadLineResources.resx').getroot().findall('data')}
assert len(resources)==245
(root/'expected-resources.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
feed=Path('/clang64/lib/dotnet/library-packs/psreadline.2.3.6.nupkg')
if feed.is_file():
    with zipfile.ZipFile(feed) as z:
        same=all(z.read(name)==(module/name).read_bytes() for name in expected)
    if same:
        installed=Path('/clang64/lib/powershell/Modules/PSReadLine/2.3.6')
        for name in expected:assert (installed/name).read_bytes()==(module/name).read_bytes(),name
        print('PASS restored installed NuGet module files equal installed loose module files')
print('PASS complete48+1 unchanged production sources/resource,9 module files,457 API declarations, original identity and five original Core forwarders retargeted to source SMA')
