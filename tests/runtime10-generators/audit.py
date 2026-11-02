"""Audit original generator source selection, resources, policies and actual inputs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root, out, check = (Path(p).resolve() for p in sys.argv[1:])
source = root / 'r'
libs = source / 'src/libraries'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((out / 'source-inputs.json').read_text())
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def posix(p):
    p = p.replace('\\', '/').rstrip('/')
    assert p.lower().startswith(base.lower() + '/'), p
    return root / p[len(base) + 1:]
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
    assert tree.findtext('.//TargetFramework') == 'netstandard2.0'
    assert 'DEBUG' not in tree.findtext('.//DefineConstants').split(';')
    assert {e.get('Include'): e.get('Version').strip('[]') for e in tree.iter('PackageReference')} == item['dependencies']
    actual = {posix(p) for p in (out / name / 'obj/Release/netstandard2.0/Compile.txt').read_text().splitlines() if p}
    assert {p for p in actual if p.is_relative_to(source)} == {source / p for p in item['original_cs']}, name
    assert any(p.name == 'ExceptionPolyfills.cs' for p in actual), name
    assert any(p.name == 'NullableAttributes.cs' for p in actual), name
    for filename in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        assert (out / name / 'bin/Release/netstandard2.0' / filename).read_bytes() == (source / filename).read_bytes()
for path in ['src/libraries/Directory.Build.targets', 'src/libraries/NetCoreAppLibrary.props', 'eng/Versions.props', 'eng/resources.targets', 'src/libraries/System.Text.Json/gen/System.Text.Json.SourceGeneration.targets', 'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    wanted[path] = sha(source / path)
ancillary = libs / 'System.Runtime.InteropServices/tests/Ancillary.Interop'
for p in [*ancillary.glob('*.cs'), ancillary / 'Ancillary.Interop.csproj', libs / 'System.Runtime.InteropServices/tests/Common/MarshalDirection.cs', libs / 'System.Runtime.InteropServices/tests/Common/ExceptionMarshalling.cs']:
    wanted[p.relative_to(source).as_posix()] = sha(p)
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
assert verified == set(wanted), set(wanted) - verified
feeds = [root / 'roslyn414-vb-4/feed', root / 'workspaces414-ns20-3/feed', root / 'roslyn414-ns20-3/feed', root / 'roslyn44-ns20-2/feed', root / 'runtime9-ns20-2/feed', root / 'humanizer-ns20-1/feed', root / 'maintenance20-1/feed', root / 'netstandard20-2/feed', out / 'platform-feed']
available = {p.name.lower(): p for feed in feeds for p in feed.glob('*.nupkg')}
cache_audits = []
for assets_file in [out / n / 'obj/project.assets.json' for n in record['projects']] + [check / 'obj/project.assets.json']:
    assets = json.loads(assets_file.read_text())
    assert len(assets['packageFolders']) == 1
    cache = posix(next(iter(assets['packageFolders'])))
    for name, entry in assets['libraries'].items():
        if entry['type'] != 'package':
            continue
        ident, version = name.split('/')
        filename = ident.lower() + '.' + version + '.nupkg'
        expected = available[filename]
        assert (cache / entry['path'] / filename).read_bytes() == expected.read_bytes(), (assets_file, name)
        with zipfile.ZipFile(expected) as z:
            for path in z.namelist():
                if path.endswith('.dll'):
                    assert (cache / entry['path'] / path).read_bytes() == z.read(path), (name, path)
        cache_audits.append(dict(project=str(assets_file.relative_to(out)), package=name, sha256=sha(expected)))
artifacts = {}
for name in record['projects']:
    folder = out / name / 'bin/Release/netstandard2.0'
    files = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*.dll') if p.name in {name + '.dll', name + '.resources.dll'}}
    assert name + '.dll' in files
    artifacts[name] = files
assert len(artifacts) == 6
results = json.loads((check / 'results.json').read_text())
assert len(results['generator_entry_points']) == 8
assert results['net10_generated_code_compiles'] and results['native_import_json_regex_net8_execution']
report = dict(original_archive_inputs_verified=len(verified), actual_producer_and_consumer_package_references_verified=len(cache_audits), package_audits=cache_audits, all_cached_source_package_and_dll_bytes_match=True, original_manifest_generators_built=6, original_generator_entry_points_checked=8, source_artifacts=artifacts, original_netstandard_polyfills_included=True, production_source_changes=0, formal_pacman_installed=False, full_dependency_goal_complete=False)
(out / 'source-package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS six original generator source/resource/policy graphs and all actual source package inputs')
