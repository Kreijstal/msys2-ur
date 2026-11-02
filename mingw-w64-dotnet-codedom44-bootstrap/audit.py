"""Audit original compile selection, policies and source-only NS2 reference bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

root = Path(sys.argv[1]).resolve()
source = root / 'source'
record = json.loads((root / 'source-inputs.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, digest in record['original_file_sha256'].items():
    assert sha(source / name) == digest, name
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def posix(value):
    value = value.replace('\\', '/').rstrip('/')
    assert value.lower().startswith(base.lower() + '/'), value
    return root / value[len(base) + 1:]
project = source / 'src/System.CodeDom/src/System.CodeDom.csproj'
expected = set()
for group in E.parse(project).getroot():
    if group.tag.rsplit('}', 1)[-1] != 'ItemGroup':
        continue
    condition = group.get('Condition')
    assert condition in {None, "'$(TargetGroup)' == 'netstandard'", "'$(TargetGroup)' == 'netfx'"}, condition
    if condition == "'$(TargetGroup)' == 'netfx'":
        continue
    for item in group:
        if item.tag.rsplit('}', 1)[-1] == 'Compile':
            assert not item.get('Condition')
            name = item.get('Include').replace('\\', '/')
            path = Path(str(source / 'src/Common/src') + name[len('$(CommonPath)'):]) if name.startswith('$(CommonPath)') else project.parent / name
            expected.add(path.resolve())
expected.add(source / 'src/Common/src/System/SR.cs')
obj = root / 'obj/Release/netstandard2.0'
actual = {posix(s) for s in (obj / 'Compile.txt').read_text().splitlines() if s}
assert {p for p in actual if p.is_relative_to(source)} == expected
assert actual - expected == {root / 'SR.Generated.cs', root / 'AssemblyInfo.g.cs'}
policy = (obj / 'policy.txt').read_text().replace('\n', ';').strip(';').split('|')
assert len(policy) == 6 and policy[:2] == ['netstandard2.0', 'netstandard'] and policy[3:] == ['1701;1702', '7.3', 'true'], policy
assert 'CODEDOM' in policy[2] and 'DEBUG' not in policy[2]
assert not (obj / 'Analyzer.txt').read_text().strip()
assets = json.loads((root / 'obj/project.assets.json').read_text())
assert not assets.get('logs')
assert set(assets['libraries']) == {'NETStandard.Library/2.0.3', 'Microsoft.NETCore.Platforms/1.1.0'}
cache = posix(next(iter(assets['packageFolders'])))
for ident, item in assets['libraries'].items():
    name = ident.lower().replace('/', '.') + '.nupkg'
    package = Path('/clang64/lib/dotnet/library-packs') / name
    assert (cache / item['path'] / name).read_bytes() == package.read_bytes()
    with zipfile.ZipFile(package) as z:
        for member in z.namelist():
            if member.endswith('.dll'):
                assert (cache / item['path'] / member).read_bytes() == z.read(member)
refs = [Path(subprocess.check_output(['cygpath', '-au', s], text=True).strip()) for s in (obj / 'ReferencePath.txt').read_text().splitlines() if s]
assert len(refs) == 113 and all(p.is_relative_to(cache / 'netstandard.library/2.0.3') for p in refs)
with zipfile.ZipFile(root / 'feed/System.CodeDom.4.4.0.nupkg') as z:
    metadata = E.fromstring(z.read('System.CodeDom.nuspec')).find('{*}metadata')
    assert metadata.findtext('{*}id') == 'System.CodeDom'
    assert metadata.findtext('{*}version') == '4.4.0'
    assert metadata.find('{*}repository').get('commit') == record['source_commit']
    assert not metadata.findall('.//{*}dependency')
    assert {s for s in z.namelist() if s.endswith('.dll')} == {'lib/netstandard2.0/System.CodeDom.dll', 'ref/netstandard2.0/System.CodeDom.dll'}
    assert z.read('lib/netstandard2.0/System.CodeDom.dll') == (root / 'bin/Release/netstandard2.0/System.CodeDom.dll').read_bytes()
    assert z.read('ref/netstandard2.0/System.CodeDom.dll') == (root / 'reference/bin/Release/netstandard2.0/System.CodeDom.dll').read_bytes()
    for lic in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        assert z.read(lic) == (source / lic).read_bytes()
report = dict(original_source_files_verified=len(record['original_file_sha256']), original_CSharp_inputs=len(expected), production_CSharp_changes=0, original_NS2_source_conditions=True, source_only_reference_archives_and_DLL_bytes=True, source_reference_assemblies=len(refs), policy=policy, bootstrap_language_version='7.3', original_buildtools_host_replayed=False, other_original_profiles_built=False, full_dependency_goal_complete=False)
(root / 'producer-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
