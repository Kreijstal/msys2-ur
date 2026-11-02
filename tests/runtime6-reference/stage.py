"""Stage audited NET6 core contracts in an isolated bootstrap reference pack."""
from pathlib import Path
import hashlib, json, shutil, sys

root, prefix = (Path(p).resolve() for p in sys.argv[1:])
prefix.mkdir()
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
name = 'dotnet-reference6-core-bootstrap'
pack = prefix / 'lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap'
doc = prefix / 'share/doc' / name
checks = doc / 'checks'
checks.mkdir(parents=True)
records = json.loads((root / 'build/results.json').read_text())
assert len(records['projects']) == 137 and not records['complete_targeting_pack_built']
validation = json.loads((root / 'check/results.json').read_text())
assert validation['all_original_metadata_and_reference_closure_checks_passed']
assert validation['NET8_only_API_rejected_by_NET6_and_accepted_by_NET8_control']
refs = pack / 'build/ref/net6.0'
refs.mkdir(parents=True)
for assembly, record in records['projects'].items():
    src = root / 'build/ref/net6.0' / (assembly + '.dll')
    assert sha(src) == record['output_sha256']
    shutil.copyfile(src, refs / src.name)
for src, dest in [('build/results.json', 'build/results.json'), ('check/results.json', 'check/results.json'),
                  ('source-audit.json', 'source-audit.json')]:
    target = pack / dest
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / src, target)
for src, dest in [('check/metadata-results.json', 'metadata-results.json'), ('check/results.json', 'validation-results.json'),
                  ('source-audit.json', 'source-audit.json')]:
    shutil.copyfile(root / src, doc / dest)
for n in ['validate.py', 'AuditMetadata.cs', 'Consumer.cs', 'check-installed.py']:
    shutil.copyfile(here / n, checks / n)
shutil.copytree(here / 'keys', checks / 'keys')
shutil.copyfile(here / 'README.md', doc / 'README.md')
source = Path(records['source_root'])
license_dir = prefix / 'share/licenses' / name
license_dir.mkdir(parents=True)
for n in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    shutil.copyfile(source / n, license_dir / n)
manifest = {p.relative_to(prefix).as_posix(): sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc / 'payload-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('PASS staged 137 original NET6 core references;', len(manifest), 'payload hashes; no SDK targeting-pack registration')
