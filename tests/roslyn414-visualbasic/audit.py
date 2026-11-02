"""Compare original archive inputs, private packages and actual compiler caches."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root, out, consumer = (Path(p).resolve() for p in sys.argv[1:])
source = root / 'roslyn414-1/roslyn-source'
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    return base + '/' + p.resolve().relative_to(root).as_posix()
def posix(path):
    path = path.replace('\\', '/').rstrip('/')
    assert path.lower().startswith(base.lower() + '/'), path
    return root / path[len(base) + 1:]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((out / 'source-inputs.json').read_text())
policy = json.loads((out / 'arcade-policy.json').read_text())
assert sha(root / policy['archive_name']) == policy['archive_sha256']
assert sha(out / 'Arcade.ProjectDefaults.props') == policy['sha256']
details = E.parse(source / 'eng/Version.Details.xml')
arcade_dependency = next(e for e in details.iter('Dependency') if e.get('Name') == 'Microsoft.DotNet.Arcade.Sdk')
assert arcade_dependency.findtext('Sha') == policy['commit']
defaults_tree = E.parse(out / 'Arcade.ProjectDefaults.props')
vb_defaults = next(e for e in defaults_tree.iter('When') if e.get('Condition') == "'$(Language)' == 'VB'")
defaults = {e.tag: e.text for e in vb_defaults.find('PropertyGroup')}
wanted = {}
projects = list(out.glob('*/**/Library.*proj'))
assert len(projects) == 5, projects
for path in projects:
    tree = E.parse(path)
    if path.suffix == '.vbproj':
        for key, value in defaults.items():
            # The original syntax generator explicitly overrides strict mode.
            expected = 'Off' if key == 'OptionStrict' and 'VBSyntaxGenerator' in path.parts else value
            assert tree.findall('.//' + key)[-1].text == expected, (path, key, expected)
    files = record['projects'][path.relative_to(out).as_posix()]
    for name, digest in files.items():
        assert sha(source / name) == digest, name
        wanted[name] = digest
    actual_file = path.parent / 'obj/Release' / tree.findtext('.//TargetFramework') / 'Compile.txt'
    actual = {posix(p).resolve() for p in actual_file.read_text().splitlines() if p}
    originals = {source / name for name in files}
    assert originals <= actual, (path, originals - actual)
    assert {p for p in actual if p.is_relative_to(source)} == originals, path
    if 'Microsoft.CodeAnalysis.VisualBasic' in path.parts or 'Microsoft.CodeAnalysis.VisualBasic.Workspaces' in path.parts:
        assert tree.findtext('.//TargetFramework') == 'netstandard2.0'
generated = {}
for path in sorted((out / 'compiler/generated').iterdir()):
    original = source / 'src/Compilers/VisualBasic/Portable/Generated' / path.name
    assert path.read_text(encoding='utf-8-sig') == original.read_text(encoding='utf-8-sig'), path
    wanted[original.relative_to(source).as_posix()] = sha(original)
    generated[path.name] = sha(path)
assert len(generated) == 6
for folder in ['src/Compilers/VisualBasic/Portable', 'src/Workspaces/VisualBasic/Portable', 'src/Tools/Source/CompilerGeneratorTools/Source/VisualBasicSyntaxGenerator', 'src/Tools/Source/CompilerGeneratorTools/Source/VisualBasicErrorFactsGenerator', 'src/Tools/Source/CompilerGeneratorTools/Source/BoundTreeGenerator']:
    for p in (source / folder).rglob('*'):
        if p.is_file() and p.suffix in {'.resx', '.xlf', '.xsd', '.xml', '.vbproj', '.csproj', '.projitems', '.txt'}:
            wanted[p.relative_to(source).as_posix()] = sha(p)
for p in (source / 'src/Compilers/VisualBasic/Portable/Symbols/EmbeddedSymbols').glob('*.vb'):
    wanted[p.relative_to(source).as_posix()] = sha(p)
for path in ['eng/targets/Settings.props', 'eng/targets/Imports.targets', 'eng/Versions.props', 'eng/Directory.Packages.props', 'eng/Version.Details.xml', 'License.txt', 'THIRD-PARTY-NOTICES.txt']:
    wanted[path] = sha(source / path)
meta = json.loads((out / 'meta/source-inputs.json').read_text())
assert sha(source / meta['original_project']) == meta['original_project_sha256']
wanted[meta['original_project']] = meta['original_project_sha256']
for path in json.loads((out / 'workspaces/source-items.json').read_text())['Microsoft.CodeAnalysis.VisualBasic.Workspaces']['imports']:
    wanted[path] = sha(source / path)
archive = root / 'roslyn-4.14.0-8edf7bcd.tar.gz'
assert sha(archive) == record['source_archive_sha256'] == '8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c'
verified = set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == record['source_commit']
    for item in tar:
        name = item.name.partition('/')[2]
        if item.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(item).read()).hexdigest() == wanted[name], name
            verified.add(name)
assert verified == set(wanted), set(wanted) - verified
feeds = [out / 'feed', root / 'workspaces414-ns20-3/feed', root / 'roslyn414-ns20-3/feed', root / 'runtime9-ns20-2/feed', root / 'humanizer-ns20-1/feed', root / 'maintenance20-1/feed', root / 'netstandard20-2/feed', out / 'platform-feed']
packages = {p.name.lower(): p for feed in feeds for p in feed.glob('*.nupkg')}
cache_records = []
for assets_file in [p.parent / 'obj/project.assets.json' for p in projects] + [out / 'meta/obj/project.assets.json', consumer / 'obj/project.assets.json']:
    assets = json.loads(assets_file.read_text())
    assert len(assets['packageFolders']) == 1
    cache = posix(next(iter(assets['packageFolders'])))
    for name, item in assets['libraries'].items():
        if item['type'] != 'package':
            continue
        ident, version = name.split('/')
        filename = ident.lower() + '.' + version + '.nupkg'
        expected = packages[filename]
        assert (cache / item['path'] / filename).read_bytes() == expected.read_bytes(), (assets_file, name)
        with zipfile.ZipFile(expected) as z:
            for path in z.namelist():
                if path.endswith('.dll'):
                    assert (cache / item['path'] / path).read_bytes() == z.read(path), (name, path)
        cache_records.append(dict(project=str(assets_file.relative_to(out)) if assets_file.is_relative_to(out) else str(assets_file), package=name, sha256=sha(expected)))
for name in ['Microsoft.CodeAnalysis.Common', 'Microsoft.CodeAnalysis.CSharp', 'Microsoft.CodeAnalysis.Workspaces.Common', 'Microsoft.CodeAnalysis.CSharp.Workspaces', 'Microsoft.CodeAnalysis.VisualBasic', 'Microsoft.CodeAnalysis.VisualBasic.Workspaces', 'Microsoft.CodeAnalysis']:
    package = packages[(name + '.4.14.0.nupkg').lower()]
    with zipfile.ZipFile(package) as z:
        spec = E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))))
        metadata = next(e for e in spec if e.tag.endswith('metadata'))
        values = {e.tag.rsplit('}', 1)[-1]: e.text for e in metadata}
        assert values['id'] == name and values['version'] == '4.14.0'
        repo = next(e for e in metadata if e.tag.endswith('repository'))
        assert repo.get('commit') == record['source_commit']
        assert all(e.get('targetFramework') == '.NETStandard2.0' for e in metadata.iter() if e.tag.endswith('group'))
        if name == 'Microsoft.CodeAnalysis':
            deps = {e.get('id'): e.get('version').strip('[]') for e in metadata.iter() if e.tag.endswith('dependency')}
            assert deps == meta['dependencies'], deps
            assert not any(p.endswith('.dll') for p in z.namelist())
        for file in ['License.txt', 'THIRD-PARTY-NOTICES.txt']:
            assert z.read(file) == (source / file).read_bytes()
        for path in z.namelist():
            if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
                assert (consumer / 'bin/Release/net8.0' / path.removeprefix('lib/netstandard2.0/')).read_bytes() == z.read(path), (name, path)
report = dict(original_archive_inputs_verified=len(verified), pinned_arcade_vb_defaults_verified=defaults, arcade_policy=policy, regenerated_original_compiler_outputs=generated, actual_compiler_and_consumer_package_references_verified=len(cache_records), all_cached_package_and_dll_bytes_match_source=True, packages=cache_records, production_source_changes=0, formal_pacman_installed=False, full_dependency_goal_complete=False)
(out / 'source-package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS original VB4.14 archive inputs and actual compiler/consumer source-package caches')
