"""Prove the JSON10-on-.NET8 implementation and compiler host use original sources."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root, out, generators, host = (Path(p).resolve() for p in sys.argv[1:])
source = root / 'r'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((out / 'source-inputs.json').read_text())
assert set(record['projects']) == {'System.Text.Json', 'System.Text.Encodings.Web', 'System.IO.Pipelines'}
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def posix(p):
    p = p.replace('\\', '/').rstrip('/')
    if p.lower().startswith(base.lower() + '/'):
        return root / p[len(base) + 1:]
    return Path(subprocess.check_output(['cygpath', '-u', p], text=True).strip())
wanted = {}
for name, item in record['projects'].items():
    assert item['production_cs_changes'] == 0
    for path, digest in {**item['original_cs'], **item['original_resources']}.items():
        assert sha(source / path) == digest, path
        wanted[path] = digest
    wanted[item['original_project']] = item['original_project_sha256']
    for path in item['key_policy']['files']:
        wanted[path] = sha(source / path)
    tree = E.parse(out / name / 'Build.csproj')
    assert tree.findtext('.//TargetFramework') == 'net8.0'
    assert 'DEBUG' not in tree.findtext('.//DefineConstants').split(';')
    actual = {posix(p) for p in (out / name / 'obj/Release/net8.0/Compile.txt').read_text().splitlines() if p}
    assert {p for p in actual if p.is_relative_to(source)} == {source / p for p in item['original_cs']}, name
    for filename in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        assert (out / name / 'bin/Release/net8.0' / filename).read_bytes() == (source / filename).read_bytes()
    assert not item['dependencies'], item['dependencies']
for path in ['src/libraries/Directory.Build.targets', 'eng/Versions.props', 'eng/resources.targets', 'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    wanted[path] = sha(source / path)
archive = root / 'runtime-v10.0.5.tar.gz'
assert sha(archive) == record['runtime_archive_sha256'] == '1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
verified = set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == record['runtime_commit']
    for member in tar:
        name = member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == wanted[name], name
            verified.add(name)
assert verified == set(wanted)
json_refs = [posix(p) for p in (out / 'System.Text.Json/obj/Release/net8.0/ReferencePath.txt').read_text().splitlines() if p]
for name in ['System.Text.Encodings.Web', 'System.IO.Pipelines']:
    selected = [p for p in json_refs if p.name == name + '.dll']
    assert len(selected) == 1 and selected[0].is_relative_to(out / name), (name, selected)
analyzers = [posix(p) for p in (out / 'System.Text.Json/obj/Release/net8.0/Analyzer.txt').read_text().splitlines() if p]
regex = generators / 'System.Text.RegularExpressions.Generator/bin/Release/netstandard2.0/System.Text.RegularExpressions.Generator.dll'
assert regex in analyzers
generated = list((out / 'System.Text.Json/generated').rglob('*.cs'))
assert generated and any('CreateIntegerRegex' in p.read_text() for p in generated)
log = (out / 'System.Text.Json/build.log').read_text()
assert not any(code in log for code in ['CS8032', 'CS8784', 'CS8785']), 'Generator load/execution warning'
host_inputs = json.loads((host / 'host-source-inputs.json').read_text())
for name, digest in host_inputs['unchanged_compiler_sha256'].items():
    assert sha(host / name) == digest == sha(root / 'cdac-bootstrap5/compiler' / name)
for name, entry in host_inputs['explicit_source_runtime_dependencies'].items():
    package = root / 'roslyn-deps9-1/feed' / (name + '.9.0.0.nupkg')
    assert sha(package) == entry['source_package_sha256']
    with zipfile.ZipFile(package) as z:
        assert (host / (name + '.dll')).read_bytes() == z.read(entry['source_asset'])
    assert sha(host / (name + '.dll')) == entry['dll_sha256']
artifacts = {name: {p.name: sha(p) for p in (out / name / 'bin/Release/net8.0').glob(name + '.dll')} for name in record['projects']}
report = dict(original_archive_inputs_verified=len(verified), original_production_source_changes=0, supported_framework='net8.0', source_artifacts=artifacts, generated_regex_files={str(p.relative_to(out)): sha(p) for p in generated}, original_regex10_generator_used=True, unchanged_compiler_and_adapter_verified=True, explicit_source_runtime9_host_dependencies_verified=True, formal_pacman_installed=False, full_dependency_goal_complete=False)
(out / 'source-build-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS original JSON10/net8 implementation source/dependency/Regex10/unchanged compiler-host audits')
