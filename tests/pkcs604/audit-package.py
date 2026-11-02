"""Audit the actual pacman archive, original source inputs and nested NuGet assets."""
from pathlib import Path
import hashlib, io, json, sys, tarfile, zipfile, xml.etree.ElementTree as E

artifact, snapshot, out = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes()) == 'b7966d5ca8035410adc673fa1f359ed973de0b70714d7db68e8172d06afc988f'
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-pkcs604/'
manifest = json.loads(files[doc + 'payload-sha256.json'])
for rel, h in manifest.items():
    assert sha(files['clang64/' + rel]) == h, rel
assert {n for n in files if n.startswith('clang64/')} == {'clang64/' + n for n in manifest} | {doc + 'payload-sha256.json'}
archive = json.loads(files[doc + 'archive.json'])
data = files['clang64/' + archive['archive']]
assert sha(data) == archive['sha256']
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert set(z.namelist()) == set(archive['members'])
    for member, h in archive['members'].items():
        assert sha(z.read(member)) == h
    md = E.fromstring(z.read('System.Security.Cryptography.Pkcs.nuspec')).find('metadata')
    assert md.findtext('version') == '6.0.4'
    dep = md.find('dependencies/group/dependency')
    assert dep.attrib == dict(id='System.Formats.Asn1', version='6.0.0')
    assert len(z.namelist()) == 9
build = json.loads(files[doc + 'build-results.json'])
with tarfile.open(snapshot) as t:
    source = json.load(t.extractfile('source-inputs.json'))
    expected = {rel: h for r in build['projects'].values() for rel, h in r['original_source_sha256'].items()}
    found = set()
    for member in t:
        rel = member.name.removeprefix('runtime/')
        if member.isfile() and rel in expected:
            assert sha(t.extractfile(member).read()) == expected[rel] == source['files'][rel]['sha256']
            found.add(rel)
    assert found == set(expected)
assert sum(len(r['original_source_sha256']) for r in build['projects'].values()) == 393
for label, member in [('windows', 'runtimes/win/lib/net6.0/'), ('portable', 'lib/net6.0/')]:
    r = build['projects'][label]
    assert r['original_production_source_changes'] == 0
    for ext, h in r['output_sha256'].items():
        assert archive['members'][member + 'System.Security.Cryptography.Pkcs.' + ext] == h
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()), payload_files=len(manifest),
    original_profile_compile_items=393, original_source_changes=0, nested_NuGet_members=9,
    original_source_output_and_NuGet_payload_hashes_verified=True, original_Asn1_minimum_600_preserved=True,
    other_original_framework_profiles_built=False, full_dependency_goal_complete=False)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
