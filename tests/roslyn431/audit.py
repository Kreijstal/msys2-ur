"""Audit original archive inputs, dependency versions and actual cached/copied bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

root, out, check = (Path(p).resolve() for p in sys.argv[1:])
source = out / 'roslyn-source'
record = json.loads((out / 'source-inputs.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def posix(p):
    p = p.replace('\\', '/').rstrip('/')
    assert p.lower().startswith(base.lower() + '/'), p
    return root / p[len(base) + 1:]
wanted = {}
for name, item in record['projects'].items():
    assert item['production_cs_changes'] == 0
    for path, digest in item['original_cs'].items():
        assert sha(source / path) == digest, path
        wanted[path] = digest
    if item.get('tool'):
        tool = source / 'src/Tools/Source/CompilerGeneratorTools/Source' / name
        for p in tool.glob('*proj'):
            wanted[p.relative_to(source).as_posix()] = sha(p)
        mode='Debug' if name=='IOperationGenerator' else 'Release'
        actual={posix(p) for p in (out/name/('obj/'+mode+'/net8.0/Compile.txt')).read_text().splitlines() if p}
        assert {p for p in actual if p.is_relative_to(source)}=={source/p for p in item['original_cs']},name
        continue
    original = source / item['original_project']
    wanted[item['original_project']] = item['original_project_sha256']
    wanted.update(item['original_resources'])
    for file in ['PublicAPI.Shipped.txt', 'PublicAPI.Unshipped.txt']:
        p = original.parent / file
        wanted[p.relative_to(source).as_posix()] = sha(p)
    tree = E.parse(out / name / 'Build.csproj')
    assert tree.findtext('.//TargetFramework') == 'netstandard2.0'
    assert tree.findtext('.//TreatWarningsAsErrors') == 'true'
    assert tree.findtext('.//Nullable') == 'enable'
    assert tree.findtext('.//Features') == 'strict'
    assert tree.findtext('.//NoWarn').endswith(';1573;1591;1701;Nullable')
    assert 'DEBUG' not in tree.findtext('.//DefineConstants').split(';')
    actual = {posix(p) for p in (out / name / 'obj/Release/netstandard2.0/Compile.txt').read_text().splitlines() if p}
    originals = {source / p for p in item['original_cs']}
    assert {p for p in actual if p.is_relative_to(source)} == originals, name
    dependencies = {e.get('Include'): e.get('Version').strip('[]') for e in tree.iter('PackageReference')}
    assert dependencies == item['resolved_dependencies']
    for ident, minimum in item['original_package_minimums'].items():
        assert tuple(map(int, dependencies[ident].split('.'))) >= tuple(map(int, minimum.split('.'))), (name, ident)
    if name == 'Microsoft.CodeAnalysis.Workspaces':
        assert not any('/Storage/SQLite/' in str(p) for p in actual)
scan = 'import os,json,sys; print(json.dumps([os.path.join(d,f) for d,_,fs in os.walk(sys.argv[1]) for f in fs if f.endswith(".projitems")]))'
source_native = base + '/' + source.relative_to(root).as_posix()
for path in json.loads(subprocess.check_output(['/clang64/bin/python.exe', '-c', scan, source_native], text=True)):
    p = posix(path)
    wanted[p.relative_to(source).as_posix()] = sha(p)
for path in ['eng/Versions.props', 'eng/targets/Settings.props', 'eng/targets/Imports.targets', 'eng/generate-compiler-code.ps1', 'License.txt', 'THIRD-PARTY-NOTICES.txt', 'src/Compilers/CSharp/Portable/Syntax/Syntax.xml', 'src/Compilers/CSharp/Portable/BoundTree/BoundNodes.xml', 'src/Compilers/Core/Portable/Operations/OperationInterfaces.xml']:
    wanted[path] = sha(source / path)
for folder in ['src/Compilers/Core/Portable/Generated', 'src/Compilers/CSharp/Portable/Generated']:
    for p in (source / folder).rglob('*.cs'):
        wanted[p.relative_to(source).as_posix()] = sha(p)
archive = root / 'roslyn-4.3.1-4bdc8414.tar.gz'
assert sha(archive) == record['source_archive_sha256'] == '0e254cc88ce10ea4293431c4df687e0c405062a7512f811e270a2b88c5b728a1'
verified = set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == record['roslyn_commit']
    for member in tar:
        name = member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == wanted[name], name
            assert sha(source / name) == wanted[name], name
            verified.add(name)
assert verified == set(wanted), set(wanted) - verified
generated_records = []
for manifest, folder in [('generated-sources.json', 'generated'), ('operation-generated-sources.json', 'operations-generated')]:
    entries = json.loads((out / manifest).read_text())
    assert len(entries) == (5 if folder == 'generated' else 3)
    for entry in entries:
        assert sha(out / folder / entry['file']) == entry['sha256']
        generated_records.append(dict(folder=folder, **entry))
feeds = [Path('/clang64/lib/dotnet/library-packs'), out/'feed']
available = {p.name.lower(): p for feed in feeds for p in feed.glob('*.nupkg')}
cache_records = []
projects = [out / name / 'obj/project.assets.json' for name in record['projects']] + [check / 'obj/project.assets.json', check / 'standard-consumer/obj/project.assets.json']
for assets_file in projects:
    assets = json.loads(assets_file.read_text())
    assert not assets.get('logs'), (assets_file, assets.get('logs'))
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
        cache_records.append(dict(project=str(assets_file.relative_to(root)), package=name, sha256=sha(expected)))
package_records = {}
for name, item in record['projects'].items():
    if item.get('tool'):
        continue
    ident = 'Microsoft.CodeAnalysis.Common' if name == 'Microsoft.CodeAnalysis' else 'Microsoft.CodeAnalysis.Workspaces.Common' if name == 'Microsoft.CodeAnalysis.Workspaces' else name
    package = available[(ident + '.4.3.1.nupkg').lower()]
    with zipfile.ZipFile(package) as z:
        spec = E.fromstring(z.read(next(p for p in z.namelist() if p.endswith('.nuspec'))))
        md = next(e for e in spec if e.tag.endswith('metadata'))
        values = {e.tag.rsplit('}', 1)[-1]: e.text for e in md}
        assert values['id'] == ident and values['version'] == '4.3.1'
        assert next(e for e in md if e.tag.endswith('repository')).get('commit') == record['roslyn_commit']
        assert all(e.get('targetFramework') == '.NETStandard2.0' for e in md.iter() if e.tag.endswith('group'))
        deps = {e.get('id'): e.get('version').strip('[]') for e in md.iter() if e.tag.endswith('dependency')}
        assert deps == item['resolved_dependencies'], (name, deps)
        for file in ['License.txt', 'THIRD-PARTY-NOTICES.txt']:
            assert z.read(file) == (source / file).read_bytes()
        for path in z.namelist():
            if path.startswith('lib/netstandard2.0/') and path.endswith('.dll'):
                assert (check / 'bin/Release/net8.0' / path.removeprefix('lib/netstandard2.0/')).read_bytes() == z.read(path), (name, path)
    package_records[ident] = dict(sha256=sha(package), original_minimums=item['original_package_minimums'], compiled_dependencies=item['resolved_dependencies'])
report = dict(original_archive_inputs_verified=len(verified), regenerated_original_sources=generated_records, ioperation_tool_configuration='Debug', source_packages=package_records, actual_compiler_and_consumer_package_references_verified=len(cache_records), package_audits=cache_records, all_cached_archives_and_dll_bytes_match_source=True, original_NS2_nullable_warning_policy_retained=True, TreatWarningsAsErrors=True, production_source_changes=0, formal_pacman_installed=bool(json.loads((check/'results.json').read_text())['formal_pacman_installed']), full_dependency_goal_complete=False)
(out / 'source-package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS original Roslyn4.3.1 archive inputs, package identities/minimums and actual compiler/consumer bytes')
