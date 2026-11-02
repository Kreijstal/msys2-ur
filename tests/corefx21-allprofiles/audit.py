"""Compare every original library profile without changing its baseline."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

archive, producer, metadata = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).parent
record = json.loads((producer / 'results.json').read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == record['source_archive_sha256']
with tarfile.open(archive) as tar:
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name, digest in record['original_file_sha256'].items():
        assert hashlib.sha256(tar.extractfile(entries[name]).read()).hexdigest() == digest
        assert hashlib.sha256((producer / 'source' / name).read_bytes()).hexdigest() == digest
total = 0
for profile, result in record['profiles'].items():
    name, framework = profile.split('/')
    expected = json.loads((here / 'inputs' / (name + '-' + framework + '-metadata.json')).read_text())[name + '.dll']
    actual = json.loads((metadata / (name + '-' + framework + '.json')).read_text())[name + '.dll']
    assert actual['identity'] == expected['identity'], (profile, 'identity')
    assert set(actual['references']) == set(expected['references']), (profile, 'references', actual['references'])
    missing, extra = set(expected['api']) - set(actual['api']), set(actual['api']) - set(expected['api'])
    assert not missing and not extra, (profile, 'missing', sorted(missing)[:10], 'extra', sorted(extra)[:10])
    canonical = lambda rows: sorted(json.dumps(x, sort_keys=True) for x in rows)
    assert canonical(actual['attributes']) == canonical(expected['attributes']), (profile, 'attributes')
    folder = producer / name / framework
    policy = (folder / 'policy.txt').read_text()
    assert framework in policy and '7.3' in policy and 'true' in policy.lower()
    for path, digest in result['reference_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    total += len(actual['api'])
    print('PASS', profile, len(actual['api']), 'original API entries; exact identity, attributes and dependencies')
assert len(record['profiles']) == 5
print('PASS all five original source implementations:', total, 'API entries; raw source and compiler reference hashes unchanged')
