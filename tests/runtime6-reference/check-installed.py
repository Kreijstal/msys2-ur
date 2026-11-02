"""Verify actual installed core contracts and fresh metadata/consumer/negative checks."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

prefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
doc = prefix / 'share/doc/dotnet-reference6-core-bootstrap'
pack = prefix / 'lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap'
manifest = json.loads((doc / 'payload-sha256.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for rel, h in manifest.items():
    assert sha(prefix / rel) == h, rel
build = out / 'build'
shutil.copytree(pack / 'build', build)
records = json.loads((build / 'results.json').read_text())
assert len(records['projects']) == 137
for name, record in records['projects'].items():
    assert sha(build / 'ref/net6.0' / (name + '.dll')) == record['output_sha256']
cmd = [sys.executable, '-X', 'utf8', doc / 'checks/validate.py', build, build, out / 'fresh-check']
with (out / 'validation.log').open('w', encoding='utf-8') as log:
    r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=420)
assert r.returncode == 0, r.returncode
results = json.loads((out / 'fresh-check/results.json').read_text())
assert results['all_original_metadata_and_reference_closure_checks_passed']
assert results['NET8_only_API_rejected_by_NET6_and_accepted_by_NET8_control']
(out / 'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd], exit_code=0,
    payload_files_verified=len(manifest), installed_core_reference_assemblies=137,
    fresh_metadata_reference_closure_consumer_and_NET8_only_negative_checks_passed=True,
    compatibility_facades_built=False, complete_targeting_pack_built=False, original_NET6_runtime_host_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS installed', len(manifest), 'payload hashes, 137 original NET6 core contracts and fresh consumer/metadata/negative checks')
