"""Check strict source builds against original immutable metadata baselines."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out, inspected = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).parent
baseline = json.loads((here / 'inputs/published-metadata.json').read_text())
actual = json.loads(inspected.read_text())
record = json.loads((out / 'source-inputs.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == record['source_archive_sha256'] == '8bf783851ac159bf7f3d5e1388ce98549352676a80a49eb681e85bcbf6bdc601'
assert record['compiler_executable'] == 'csc34.cmd', 'Seed libraries do not pass the production audit'
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == record['source_commit']
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name, project in record['projects'].items():
        for group in ['compile_inputs', 'resource_inputs']:
            for path, digest in project[group].items():
                assert hashlib.sha256(tar.extractfile(entries[path]).read()).hexdigest() == digest
                assert sha(out / 'source' / path) == digest
        for path, projection in project.get('windows_checkout_resource_projections', {}).items():
            expected = tar.extractfile(entries[path]).read().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            assert (out / projection['path']).read_bytes() == expected
            assert sha(out / projection['path']) == projection['sha256']
        properties = E.parse(out / name / 'Build.csproj')
        for key, expected in dict(TargetFramework='netstandard2.0', LangVersion='8.0', WarningLevel='4',
                                  NoWarn='1573;1591;1701', TreatWarningsAsErrors='true', CscToolExe='csc34.cmd',
                                  PublicSign='true', Nullable='disable', Features='strict,IOperation').items():
            assert properties.findtext('.//' + key) == expected, (name, key)
        want, got = baseline[name + '.dll'], actual[name + '.dll']
        assert got['identity'] == want['identity'], name
        assert set(got['references']) == set(want['references']), (name, 'dependency identities', got['references'], want['references'])
        missing, extra = set(want['api']) - set(got['api']), set(got['api']) - set(want['api'])
        assert not missing and not extra, (name, 'API missing', sorted(missing)[:15], 'extra', sorted(extra)[:15])
        canonical = lambda values: sorted(json.dumps(x, sort_keys=True) for x in values)
        assert canonical(got['attributes']) == canonical(want['attributes']), (name, 'assembly attributes')
        print('PASS', name, len(got['api']), 'original public API entries; exact identity, attributes and dependencies;', len(project['compile_inputs']), 'unchanged C# inputs')
print('PASS original source hashes, NS2/C#8 settings, strict warnings and original 3.4 compiler')
