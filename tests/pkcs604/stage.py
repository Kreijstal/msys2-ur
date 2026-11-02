"""Stage original NET6 Pkcs profiles and reference assets with original dependency minimums."""
from pathlib import Path
import hashlib, json, shutil, sys, xml.etree.ElementTree as E, zipfile

root, prefix = (Path(p).resolve() for p in sys.argv[1:])
prefix.mkdir()
here = Path(__file__).resolve().parent
name = 'System.Security.Cryptography.Pkcs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = json.loads((root / 'plan/source-inputs.json').read_text())
source = Path(inputs['source_root'])
build = json.loads((root / 'build/results.json').read_text())
api = json.loads((root / 'api/results.json').read_text())
runtime = json.loads((root / 'check/results.json').read_text())
assert runtime['both_original_NET6_profiles_tested_on_source_NET8_and_NET10']
assert all(c['exit_code'] == 0 for c in runtime['commands'])
doc = prefix / 'share/doc/dotnet-pkcs604'
checks = doc / 'checks'
checks.mkdir(parents=True)
for n in ['check.py', 'Check.cs', 'check-api.py', 'CompareApi.cs', 'check-restore.py', 'check-installed.py', 'Microsoft.pubkey.hex']:
    shutil.copyfile(here / n, checks / n)
shutil.copytree(here / 'inputs', checks / 'inputs')
shutil.copyfile(here / 'README.md', doc / 'README.md')
for rel, dest in [('build/results.json', 'build-results.json'), ('api/results.json', 'api-results.json'),
                  ('check/results.json', 'runtime-results.json'), ('source-audit.json', 'source-audit.json')]:
    shutil.copyfile(root / rel, doc / dest)
files = set(api['original_contract_source_sha256']) | {
    'src/libraries/System.Security.Cryptography.Pkcs/ref/System.Security.Cryptography.Pkcs.csproj',
    'src/libraries/System.Security.Cryptography.Pkcs/src/Resources/Strings.resx'}
for rel in files:
    target = doc / 'validation-source' / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / rel, target)
contract = root / 'api/contract' / (name + '.dll')
assert sha(contract) == api['reference_contract_sha256']
binary = prefix / 'lib/dotnet/library-packs/pkcs-6.0.4-net6-bootstrap'
members = {'ref/net6.0/' + name + '.dll': contract.read_bytes()}
for label, member in [('windows', 'runtimes/win/lib/net6.0/'), ('portable', 'lib/net6.0/')]:
    record = build['projects'][label]
    comparison = api['projects'][label]
    assert record['original_production_source_changes'] == 0 and comparison['exit_code'] == 0
    assert comparison['comparison']['expected_entries'] == 383
    assert comparison['comparison']['total_differences'] == 0
    assert not comparison['comparison']['nullable_annotation_differences']
    for ext in ['dll', 'pdb', 'xml']:
        f = root / 'build' / label / 'bin' / (name + '.' + ext)
        assert sha(f) == record['output_sha256'][ext]
        members[member + f.name] = f.read_bytes()
        dest = binary / label / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)
    assert comparison['implementation_sha256'] == record['output_sha256']['dll']
(binary / 'ref').mkdir()
shutil.copyfile(contract, binary / 'ref' / contract.name)
meta = E.Element('package')
md = E.SubElement(meta, 'metadata')
for k, v in dict(id=name, version='6.0.4', authors='Microsoft',
    description='Original Pkcs 6.0.4 NET6 Windows and portable source bootstrap').items():
    E.SubElement(md, k).text = v
E.SubElement(md, 'license', type='expression').text = 'MIT'
E.SubElement(md, 'repository', type='git', url='https://github.com/dotnet/runtime', commit='e37fab9fc9f7bce120a7165491ed392a73f8ab51')
group = E.SubElement(E.SubElement(md, 'dependencies'), 'group', targetFramework='net6.0')
E.SubElement(group, 'dependency', id='System.Formats.Asn1', version='6.0.0')
members[name + '.nuspec'] = E.tostring(meta, encoding='utf-8', xml_declaration=True)
members['LICENSE.TXT'] = (source / 'LICENSE.TXT').read_bytes()
archive = prefix / 'lib/dotnet/library-packs/system.security.cryptography.pkcs.6.0.4.nupkg'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for member, data in sorted(members.items()):
        item = zipfile.ZipInfo(member, (2000, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(item, data)
(doc / 'archive.json').write_text(json.dumps(dict(archive=archive.relative_to(prefix).as_posix(), sha256=sha(archive),
    members={k: hashlib.sha256(v).hexdigest() for k, v in members.items()}), indent=2) + '\n')
license_dir = prefix / 'share/licenses/dotnet-pkcs604'
license_dir.mkdir(parents=True)
for n in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    shutil.copyfile(source / n, license_dir / n)
manifest = {p.relative_to(prefix).as_posix(): sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc / 'payload-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('PASS staged original NET6 reference, Windows and portable assets;', len(manifest), 'payload hashes')
