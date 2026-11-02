"""Prepare original VB 4.14 projects using the source-built NS2 dependency graph."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(), out
source=out/'roslyn-source'
archive = root / 'roslyn-4.14.0-8edf7bcd.tar.gz'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c'
out.mkdir()
here = Path(__file__).resolve().parent
native_archive=subprocess.check_output(['cygpath','-am',str(archive)],text=True).strip()
native_out=subprocess.check_output(['cygpath','-am',str(out)],text=True).strip()
native_extract=subprocess.check_output(['cygpath','-am',str(here/'extract-source.py')],text=True).strip()
subprocess.run(['/clang64/bin/python.exe',native_extract,native_archive,native_out],check=True)
policy = json.loads((here / 'inputs/arcade-policy.json').read_text())
arcade = root / policy['archive_name']
assert sha(arcade) == policy['archive_sha256']
with tarfile.open(arcade) as tar:
    assert tar.pax_headers['comment'] == policy['commit']
    member = next(m for m in tar if m.name.partition('/')[2] == policy['path'])
    original_policy = tar.extractfile(member).read()
assert hashlib.sha256(original_policy).hexdigest() == policy['sha256']
assert original_policy == (here / 'inputs/arcade-ProjectDefaults.props').read_bytes()
(out / 'Arcade.ProjectDefaults.props').write_bytes(original_policy)
(out / 'arcade-policy.json').write_text(json.dumps(policy, indent=2) + '\n')
for kind in ['compiler', 'workspaces']:
    subprocess.run([sys.executable, str(here / f'inputs/prepare-{kind}.py'), str(source), str(out / kind)], check=True)
native_root = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    p=p.resolve()
    if p.is_relative_to(root):return native_root+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
feeds=[out/'feed',Path('/clang64/lib/dotnet/library-packs')]
(out / 'feed').mkdir()
config = E.Element('configuration')
sources = E.SubElement(config, 'packageSources')
E.SubElement(sources, 'clear')
for i, path in enumerate(feeds):
    E.SubElement(sources, 'add', key=f'source{i}', value=native(path))
E.indent(config)
for folder in [out, out / 'compiler', out / 'workspaces']:
    E.ElementTree(config).write(folder / 'NuGet.config', encoding='utf-8', xml_declaration=True)
records = {}
for project in [*out.glob('compiler/*/Library.*proj'),*out.glob('workspaces/*/Library.*proj')]:
    tree = E.parse(project)
    files = {}
    for item in tree.iter('Compile'):
        path = item.get('Include', '').replace('\\', '/')
        if path.startswith(native(source) + '/') and '*' not in path:
            original = source / path[len(native(source)) + 1:]
            files[original.relative_to(source).as_posix()] = sha(original)
    records[project.relative_to(out).as_posix()] = files
(out / 'source-inputs.json').write_text(json.dumps(dict(source_commit='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b', source_archive_sha256=sha(archive), projects=records, production_source_changes=0, complete=False,full_dependency_goal_complete=False), indent=2) + '\n')
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
(out/'tool-inputs.json').write_text(json.dumps({str(p):dict(owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip(),sha256=sha(p)) for p in [Path('/clang64/lib/dotnet/sdk/8.0.131/Roslyn/bincore/vbc.dll'),*[compiler/n for n in ['CompilerHost.dll','Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]]},indent=2)+'\n')
print('Prepared VB4.14', {name: len(files) for name, files in records.items()}, flush=True)
