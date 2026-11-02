"""Check the installed compiler package against its archive and build records."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

archive, prepared, output = (Path(p).resolve() for p in sys.argv[1:])
names = subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines()
prefix = 'clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/'
docs = 'clang64/share/doc/dotnet-compiler5-bootstrap/'
licenses = 'clang64/share/licenses/dotnet-compiler5-bootstrap/'
files = [name for name in names if not name.endswith('/')]
assert len(files) == len(set(files))
records = {}
for name in files:
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    if name.startswith('.'):
        assert name in {'.PKGINFO', '.BUILDINFO', '.MTREE'}, name
        continue
    assert name.startswith((prefix, docs, licenses)), name
    assert not name.lower().endswith(('.pdb', '.exe.config')), name
    assert not name.endswith('csc50-build.cmd'), name
    data = subprocess.check_output(['bsdtar', '-xOf', str(archive), name])
    installed = Path('/') / name
    assert installed.read_bytes() == data, name
    records[name] = hashlib.sha256(data).hexdigest()
assets = json.loads((prepared / 'host-assets.json').read_text())
for name, digest in assets['runtime9_assets_sha256'].items():
    assert records[prefix + name + '.dll'] == digest
baseline = json.loads((prepared / 'source-inputs.json').read_text())
for name in ['csc.exe', 'Microsoft.CodeAnalysis.dll', 'Microsoft.CodeAnalysis.CSharp.dll']:
    assert records[prefix + name] == baseline['installed_compiler_files_sha256'][name]
wrapper = (Path('/') / prefix / 'csc50.cmd').read_text()
assert '%~dp0' in wrapper and ':/' not in wrapper and ':\\' not in wrapper
assert len([name for name in records if name.startswith(licenses)]) == 7
report = dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              installed_files_verified=len(records), installed_files_sha256=records,
              all_files_inside_dedicated_compiler_docs_license_paths=True,
              inherited_compiler_bytes_match_declared_owner=True,
              runtime9_bytes_match_fresh_source_build=True,
              relative_installed_wrapper=True, full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS installed package archive, compiler provenance, source runtime9 assets and dedicated paths')
