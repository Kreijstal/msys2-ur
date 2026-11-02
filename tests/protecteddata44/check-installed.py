"""Verify installed bytes, real cached NuGet assets, both runtimes and reference contracts."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, zipfile

prefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
doc = prefix / 'share/doc/dotnet-protecteddata44'
checks = doc / 'checks'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((doc / 'payload-sha256.json').read_text())
for rel, h in manifest.items():
    assert sha(prefix / rel) == h, rel
archive = json.loads((doc / 'archive.json').read_text())
assert sha(prefix / archive['archive']) == archive['sha256']
with zipfile.ZipFile(prefix / archive['archive']) as z:
    assert set(z.namelist()) == set(archive['members'])
    for member, h in archive['members'].items():
        assert hashlib.sha256(z.read(member)).hexdigest() == h, member
commands = []

def run(label, cmd):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=420)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)

run('restore', [sys.executable, '-X', 'utf8', checks / 'check-restore.py', prefix, out / 'restore'])
source = out / 'validation-source'
shutil.copytree(doc / 'validation-source', source)
cache = out / 'restore/cache/system.security.cryptography.protecteddata/4.4.0'
name = 'System.Security.Cryptography.ProtectedData'
contract = cache / 'ref/netstandard2.0' / (name + '.dll')
for label, member in [('windows', 'runtimes/win/lib/netstandard2.0'), ('portable', 'lib/netstandard2.0')]:
    build = out / label
    (build / 'bin').mkdir(parents=True)
    record = json.loads((doc / (label + '-build-results.json')).read_text())
    record['source_root'] = source.as_posix()
    record['contract_reference_path'] = contract.as_posix()
    (build / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    for ext in ['dll', 'pdb']:
        f = cache / member / (name + '.' + ext)
        assert sha(f) == record['output_sha256'][ext]
        shutil.copyfile(f, build / 'bin' / f.name)
    script = 'check.py' if label == 'windows' else 'check-portable.py'
    run(label + '-runtime', [sys.executable, '-X', 'utf8', checks / script, build, out / (label + '-runtime')])
    run(label + '-api', [sys.executable, '-X', 'utf8', checks / 'check-api.py', build, out / (label + '-api')])
run('windows-net10', [sys.executable, '-X', 'utf8', checks / 'check.py', out / 'windows', out / 'windows-net10', '--net10'])
reference = out / 'reference'
(reference / 'bin').mkdir(parents=True)
shutil.copyfile(contract, reference / 'bin' / contract.name)
(reference / 'results.json').write_text(json.dumps(dict(source_root=source.as_posix())) + '\n')
run('reference-api', [sys.executable, '-X', 'utf8', checks / 'check-api.py', reference, out / 'reference-api'])
for label in ['windows', 'portable', 'reference']:
    api = json.loads((out / (label + '-api/results.json')).read_text())
    assert api['exit_code'] == 0 and api['comparison']['expected_entries'] == 7
    assert api['comparison']['total_differences'] == 0 and not api['comparison']['nullable_annotation_differences']
(out / 'results.json').write_text(json.dumps(dict(commands=commands, payload_files_verified=len(manifest),
    exact_NuGet_archive_and_cached_asset_bytes_verified=True, NET10_strict_restore_RID_selection_verified=True,
    cached_Windows_implementation_executed_on_NET8_and_NET10=True, cached_portable_PNSE_implementation_executed=True,
    Windows_portable_and_reference_CLR_and_nullable_entries=21, strict_CLR_and_nullable_comparison_passed=True,
    runtime_consumers_compiled_against_actual_cached_NuGet_reference_asset=True,
    Windows_native_DPAPI_empty_input_regression_and_interop_passed=True, original_absence_of_TFA_preserved=True,
    neutral_resource_sets=2, neutral_resource_values=4, portable_PDB_associations=2, original_NETFramework_and_harvested_profiles_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS', len(manifest), 'payload hashes, source NuGet cache/RID selection, cached reference/Windows NET8/NET10 and portable execution, 21 strict API entries')
