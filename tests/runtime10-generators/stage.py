"""Stage the original six analyzer assemblies and satellites as a reviewable bundle."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

root, out, stage = (Path(p).resolve() for p in sys.argv[1:])
assert not stage.exists(), stage
record = json.loads((out / 'source-inputs.json').read_text())
audit = json.loads((out / 'source-package-audit.json').read_text())
assert audit['original_manifest_generators_built'] == 6
destination = stage / 'analyzers/dotnet/cs'
destination.mkdir(parents=True)
files = {}
for name in record['projects']:
    source = out / name / 'bin/Release/netstandard2.0'
    for path in source.rglob('*.dll'):
        if path.name not in {name + '.dll', name + '.resources.dll'}:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert target.read_bytes() == path.read_bytes()
        files[target.relative_to(stage).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
for name in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    target = stage / name
    shutil.copyfile(root / 'r' / name, target)
    files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
assert sum('/' not in Path(p).relative_to('analyzers/dotnet/cs').as_posix() for p in files if p.startswith('analyzers/')) == 6
manifest = dict(version='10.0.5', source_commit=record['runtime_commit'], source_archive_sha256=record['runtime_archive_sha256'], files=files, unchanged_source_assemblies=True, formal_pacman_installed=False, complete_targeting_pack_built=False, full_dependency_goal_complete=False)
(stage / 'source-artifacts.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('PASS staged six source generator assemblies, original satellites/licenses and exact hashes:', len(files), 'files')
