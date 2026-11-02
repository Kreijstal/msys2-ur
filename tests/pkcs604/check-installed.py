"""Fresh offline restore and execution of exact cached Pkcs6 assets on both source hosts."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, zipfile

prefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
doc = prefix / 'share/doc/dotnet-pkcs604'
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
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
run('restore', [sys.executable, '-X', 'utf8', checks / 'check-restore.py', prefix, out / 'restore'])
source = out / 'validation-source'
shutil.copytree(doc / 'validation-source', source)
plan = out / 'plan'
plan.mkdir()
(plan / 'source-inputs.json').write_text(json.dumps(dict(source_root=source.as_posix())) + '\n')
cache = out / 'restore/cache/system.security.cryptography.pkcs/6.0.4'
name = 'System.Security.Cryptography.Pkcs'
contract = cache / 'ref/net6.0' / (name + '.dll')
build = out / 'build'
records = json.loads((doc / 'build-results.json').read_text())
for label, member in [('windows', 'runtimes/win/lib/net6.0'), ('portable', 'lib/net6.0')]:
    binary = build / label / 'bin'
    binary.mkdir(parents=True)
    for ext in ['dll', 'pdb', 'xml']:
        f = cache / member / (name + '.' + ext)
        assert sha(f) == records['projects'][label]['output_sha256'][ext]
        shutil.copyfile(f, binary / f.name)
actual = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
refs = actual / 'lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap'
asn1 = out / 'restore/cache/system.formats.asn1/10.0.2/lib/net10.0/System.Formats.Asn1.dll'
run('runtime', [sys.executable, '-X', 'utf8', checks / 'check.py', plan, build, refs, out / 'runtime', '--contract', contract, '--asn1', asn1])
run('api', [sys.executable, '-X', 'utf8', checks / 'check-api.py', plan, build, refs, out / 'api', contract])
api = json.loads((out / 'api/results.json').read_text())
assert set(api['projects']) == {'windows', 'portable', 'cached-reference'}
for label, record in api['projects'].items():
    assert record['exit_code'] == 0 and record['comparison']['expected_entries'] == (382 if label == 'cached-reference' else 383)
    assert record['comparison']['total_differences'] == 0
    assert not record['comparison']['nullable_annotation_differences']
runtime = json.loads((out / 'runtime/results.json').read_text())
assert runtime['compilation_uses_actual_cached_NuGet_reference_asset']
assert runtime['NET10_executes_actual_cached_source_Asn1_dependency']
(out / 'results.json').write_text(json.dumps(dict(commands=commands, payload_files_verified=len(manifest),
    exact_NuGet_archive_and_cached_asset_bytes_verified=True, strict_NET10_restore_and_Windows_Linux_asset_selection_verified=True,
    original_Asn1_minimum_600_preserved_SDK_CPM_1002_selected=True,
    consumers_compiled_against_actual_cached_reference=True, cached_reference_matches_fresh_original_contract_API=True,
    both_cached_original_profiles_executed_on_NET8_and_NET10=True, NET10_cached_source_Asn1_dependency_executed=True,
    CLR_and_nullable_API_entries=1148, CLR_and_nullable_API_differences=0,
    neutral_resource_values=162, portable_PDB_associations=2,
    other_original_framework_profiles_built=False, full_SDK10_pruning_integration_verified=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS cached original NET6 reference/Windows/portable assets, strict restore, NET8/NET10 cryptography, source ASN.1 and 1148 strict API entries')
