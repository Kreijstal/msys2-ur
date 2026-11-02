"""Stage exact-version NETStandard2 reference, portable and Windows NuGet assets."""
from pathlib import Path
import hashlib, json, shutil, sys, xml.etree.ElementTree as E, zipfile

root, prefix = (Path(p).resolve() for p in sys.argv[1:])
prefix.mkdir()
here = Path(__file__).resolve().parent
name = 'System.Security.Cryptography.ProtectedData'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
w = json.loads((root / 'windows/results.json').read_text())
p = json.loads((root / 'portable/results.json').read_text())
source = Path(w['source_root'])
doc = prefix / 'share/doc/dotnet-protecteddata44'
checks = doc / 'checks'
checks.mkdir(parents=True)
for n in ['check.py', 'Check.cs', 'check-portable.py', 'CheckPortable.cs', 'check-api.py', 'CompareApi.cs',
          'check-restore.py', 'check-installed.py', 'Microsoft.pubkey.hex']:
    shutil.copyfile(here / n, checks / n)
for n in ['0001-handle-empty-input-in-native-DPAPI.patch', 'empty-input-fix-upstream.cs.txt', 'README.md']:
    shutil.copyfile(here / n, doc / n)
for label in ['windows', 'portable']:
    for n in ['results.json']:
        shutil.copyfile(root / label / n, doc / (label + '-build-results.json'))
    for kind in ['check', 'api']:
        data = json.loads((root / (label + '-' + kind) / 'results.json').read_text())
        if kind == 'api':
            assert data['exit_code'] == 0 and data['comparison']['expected_entries'] == 7
            assert data['comparison']['total_differences'] == 0 and not data['comparison']['nullable_annotation_differences']
            assert data['reference_contract_sha256'] == sha(root / (label + '-api/ref') / (name + '.dll'))
            assert data['implementation_sha256'] == sha(root / label / 'bin' / (name + '.dll'))
        else:
            assert all(c['exit_code'] == 0 for c in data['commands'])
        shutil.copyfile(root / (label + '-' + kind) / 'results.json', doc / (label + '-' + kind + '-results.json'))
shutil.copyfile(root / 'source-audit.json', doc / 'source-audit.json')
regression = json.loads((root / 'regression/results.json').read_text())
assert regression['original_source_empty_input_failure_reproduced_after_native_success']
assert regression['expected_negative_case_exit_code'] != 0
shutil.copyfile(root / 'regression/results.json', doc / 'empty-input-regression-results.json')
validation = doc / 'validation-source'
for rel in ['src/System.Security.Cryptography.ProtectedData/ref/System.Security.Cryptography.ProtectedData.cs',
            'src/System.Security.Cryptography.ProtectedData/ref/System.Security.Cryptography.ProtectedData.csproj',
            'src/System.Security.Cryptography.ProtectedData/src/Resources/Strings.resx']:
    f = validation / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / rel, f)
binary = prefix / 'lib/dotnet/library-packs/protecteddata-4.4.0-netstandard2-bootstrap'
for label in ['windows', 'portable']:
    shutil.copytree(root / label / 'bin', binary / label)
(binary / 'ref').mkdir()
contract = root / 'windows-api/ref' / (name + '.dll')
shutil.copyfile(contract, binary / 'ref' / contract.name)
meta = E.Element('package')
md = E.SubElement(meta, 'metadata')
for k, v in dict(id=name, version='4.4.0', authors='Microsoft',
    description='CoreFX ProtectedData4.4.0 NETStandard2 source bootstrap; Windows empty-input backport; portable PNSE profile').items():
    E.SubElement(md, k).text = v
E.SubElement(md, 'license', type='expression').text = 'MIT'
E.SubElement(md, 'repository', type='git', url='https://github.com/dotnet/corefx', commit=w['source_commit'])
E.SubElement(E.SubElement(md, 'dependencies'), 'group', targetFramework='netstandard2.0')
members = {name + '.nuspec': E.tostring(meta, encoding='utf-8', xml_declaration=True),
           'LICENSE.TXT': (source / 'LICENSE.TXT').read_bytes(),
           'ref/netstandard2.0/' + name + '.dll': contract.read_bytes()}
for label, path in [('windows', 'runtimes/win/lib/netstandard2.0/'), ('portable', 'lib/netstandard2.0/')]:
    for ext in ['dll', 'pdb']:
        f = root / label / 'bin' / (name + '.' + ext)
        members[path + f.name] = f.read_bytes()
archive = prefix / 'lib/dotnet/library-packs/system.security.cryptography.protecteddata.4.4.0.nupkg'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for member, data in members.items():
        item = zipfile.ZipInfo(member, (2000, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(item, data)
(doc / 'archive.json').write_text(json.dumps(dict(archive=archive.relative_to(prefix).as_posix(), sha256=sha(archive),
    members={k: hashlib.sha256(v).hexdigest() for k, v in members.items()}), indent=2) + '\n')
license_dir = prefix / 'share/licenses/dotnet-protecteddata44'
license_dir.mkdir(parents=True)
for n in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    shutil.copyfile(source / n, license_dir / n)
manifest = {p.relative_to(prefix).as_posix(): sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc / 'payload-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('PASS staged original-version reference, Windows and portable source assets;', len(manifest), 'payload hashes')
