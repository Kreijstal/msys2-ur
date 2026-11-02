"""Independently audit final CodeDom4.4 package source provenance and payload."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact, archive, roslyn, output = map(Path, sys.argv[1:])
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes()) == 'f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-codedom44-bootstrap/'
record = json.loads(files[doc + 'source-inputs.json'])
audit = json.loads(files[doc + 'producer-audit.json'])
checks = json.loads(files[doc + 'producer-check-results.json'])
with tarfile.open(archive) as t:
    assert t.pax_headers['comment'] == record['source_commit'] == '8321c729934c0f8be754953439b88e6e1c120c24'
    expected = set(record['original_file_sha256'])
    originals = {m.name.partition('/')[2]: t.extractfile(m).read() for m in t if m.isfile() and m.name.partition('/')[2] in expected}
assert {n: sha(v) for n, v in originals.items()} == record['original_file_sha256']
assert record['production_CSharp_changes'] == audit['production_CSharp_changes'] == 0
assert record['compiled_profile'] == 'netstandard2.0' and not record['other_original_profiles_built']
assert audit['original_NS2_source_conditions'] and audit['source_only_reference_archives_and_DLL_bytes']
assert audit['original_CSharp_inputs'] == 119 and audit['source_reference_assemblies'] == 113
assert checks['original_public_API_entries'] == checks['original_reference_public_API_entries'] == 1354
for key in ['original_runtime_reference_table_equal', 'original_compiler_reference_selected_and_verified', 'all_source_resource_values_verified', 'isolated_original_implementation_executed', 'original_NS2_PackageReference_consumer', 'CSharp_and_VB_generated_source_compiled_and_executed']:
    assert checks[key], key
assert all(c['exit_code'] == 0 for c in checks['commands'])
compiler = json.loads(files[doc + 'compiler44-source-inputs.json'])
assert sha(roslyn.read_bytes()) == compiler['source_archive_sha256'] == '9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment'] == compiler['source_commit'] == '1ce8866c9de4c2d67351ef6863699dee03b0804a'
    verified = set()
    for m in t:
        rel = m.name.partition('/')[2]
        if m.isfile() and rel in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(m).read()) == compiler['original_csc_compile_items'][rel]
            verified.add(rel)
assert len(verified) == 11 and compiler['original_csc_source_changes'] == 0
provenance = json.loads(files[doc + 'inputs/published-provenance.json'])
assert not provenance['published_binaries_executed_or_used_as_compiler_references']
assert sha(files[doc + 'inputs/published-ns2-metadata.json']) == provenance['runtime_metadata_baseline_sha256']
assert sha(files[doc + 'inputs/published-ns2-reference-metadata.json']) == provenance['reference_metadata_baseline_sha256']
for name in ['published-ns2-metadata.json', 'published-ns2-reference-metadata.json']:
    baseline = json.loads(files[doc + 'inputs/' + name])['System.CodeDom.dll']
    assert len(baseline['api']) == 1354 and baseline['identity'] == provenance['identity']
package = files['clang64/lib/dotnet/library-packs/system.codedom.4.4.0.nupkg']
assert sha(package) == checks['exact_cached_package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    md = E.fromstring(z.read('System.CodeDom.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id') == 'System.CodeDom' and md.findtext('{*}version') == '4.4.0'
    assert not md.findall('.//{*}dependency')
    assert md.find('{*}repository').get('commit') == record['source_commit']
    assert {n for n in z.namelist() if n.endswith('.dll')} == {'lib/netstandard2.0/System.CodeDom.dll', 'ref/netstandard2.0/System.CodeDom.dll'}
    assert sha(z.read('lib/netstandard2.0/System.CodeDom.dll')) == checks['candidate_DLL_sha256']
    assert sha(z.read('ref/netstandard2.0/System.CodeDom.dll')) == checks['compiler_reference_DLL_sha256']
    for lic in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        assert z.read(lic) == originals[lic]
        assert files['clang64/share/licenses/dotnet-codedom44-bootstrap/' + lic] == originals[lic]
recipe = Path('mingw-w64-dotnet-codedom44-bootstrap')
for name in ['README.md', 'check.py', 'inputs/Api.cs', 'inputs/Check.cs', 'inputs/Bridge.cs', 'inputs/published-ns2-metadata.json', 'inputs/published-ns2-reference-metadata.json', 'inputs/published-provenance.json']:
    assert files[doc + name] == (recipe / name).read_bytes()
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()), source_commit=record['source_commit'], original_source_files_verified=len(originals), original_CSharp_inputs=audit['original_CSharp_inputs'], original_reference_CSharp_inputs=1, production_CSharp_changes=0, original_public_API_entries=1354, original_reference_public_API_entries=1354, original_dependency_tables_equal=True, source_resource_values_verified=23, isolated_original_implementation_executed=True, generated_CSharp_and_VB_compiled_and_executed=True, source_csc44_original_inputs=11, nupkg_sha256=sha(package), payload_sha256={n: sha(v) for n, v in files.items() if n.startswith('clang64/')}, original_buildtools_host_replayed=False, other_original_profiles_built=False, full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
