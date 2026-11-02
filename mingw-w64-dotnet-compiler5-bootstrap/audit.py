"""Verify compiled runtime9 inputs and unchanged installed Compiler5 provenance."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile

archive, out = (Path(p).resolve() for p in sys.argv[1:])
source = out / 'runtime-source'
record = json.loads((out / 'source-inputs.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == record['runtime_archive_sha256'] == '32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
base = subprocess.check_output(['cygpath', '-am', str(out)], text=True).strip()
def posix(p):
    p = p.replace('\\', '/')
    assert p.lower().startswith(base.lower() + '/'), p
    return out / p[len(base) + 1:]
wanted = {}
for name, item in record['projects'].items():
    assert item['production_source_changes'] == 0
    for path, digest in {**item['original_cs'], **item['original_resx']}.items():
        assert sha(source / path) == digest, path
        wanted[path] = digest
    wanted[item['original_project']] = item['original_project_sha256']
    actual = {posix(p) for p in (out / name / 'obj/Release/net8.0/Compile.txt').read_text().splitlines() if p}
    assert {p for p in actual if p.is_relative_to(source)} == {source / p for p in item['original_cs']}, name
for path in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    wanted[path] = sha(source / path)
verified = set()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == record['runtime_commit']
    for member in tar:
        name = member.name.partition('/')[2]
        if member.isfile() and name in wanted:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == wanted[name], name
            verified.add(name)
assert verified == set(wanted)
compiler = out / 'compiler'
original = Path('/clang64/lib/dotnet-bootstrap/roslyn-5.0.0')
changed = {'System.Collections.Immutable.dll', 'System.Reflection.Metadata.dll'}
for path, digest in record['installed_compiler_files_sha256'].items():
    assert sha(original / path) == digest, path
    if path not in changed:
        assert sha(compiler / path) == digest, path
for name, digest in json.loads((out / 'host-assets.json').read_text())['runtime9_assets_sha256'].items():
    assert sha(compiler / (name + '.dll')) == digest == sha(out / name / 'bin/Release/net8.0' / (name + '.dll'))
report = dict(runtime_archive_sha256=sha(archive), original_archive_inputs_verified=len(verified), original_compiler_package_owner=record['installed_compiler_owner'], original_compiler_files_unchanged_except_declared_source_runtime_dependencies=True, original_production_source_changes=0, runtime9_sources_compiled={n: len(v['original_cs']) for n, v in record['projects'].items()}, installed_check_required=True, full_dependency_goal_complete=False)
(out / 'source-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS original runtime9 archive inputs and installed source Compiler5 provenance')
