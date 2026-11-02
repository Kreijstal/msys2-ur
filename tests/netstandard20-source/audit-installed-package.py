"""Check the exact reference package payload after installation."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

archive, output = (Path(p).resolve() for p in sys.argv[1:])
names = subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines()
allowed = ('clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/',
           'clang64/lib/dotnet/library-packs/netstandard.library.2.0.3.nupkg',
           'clang64/share/doc/dotnet-netstandard-reference/',
           'clang64/share/licenses/dotnet-netstandard-reference/')
assert len(names) == len(set(names))
records = {}
for name in names:
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    if name.endswith('/'):
        continue
    if name.startswith('.'):
        assert name in {'.PKGINFO', '.BUILDINFO', '.MTREE'}, name
        continue
    assert name == allowed[1] or name.startswith((allowed[0], allowed[2], allowed[3])), name
    data = subprocess.check_output(['bsdtar', '-xOf', str(archive), name])
    assert (Path('/') / name).read_bytes() == data, name
    records[name] = hashlib.sha256(data).hexdigest()
refs = [name for name in records if name.endswith('.dll')]
assert len(refs) == 113 and all('/ref/netstandard2.0/' in name for name in refs)
assert len(records) == 123
assert len([name for name in records if name.startswith(allowed[3])]) == 2
report = dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              installed_payload_files_verified=len(records), installed_reference_dlls_verified=113,
              installed_files_sha256=records, dedicated_paths_verified=True,
              full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS installed package archive bytes, 113 reference DLLs and dedicated paths')
