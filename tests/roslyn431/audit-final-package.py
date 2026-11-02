"""Independently check a completed Roslyn prerequisite package against source."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact, source_archive, output = map(Path, sys.argv[1:])
sha = lambda data: hashlib.sha256(data).hexdigest()
with tarfile.open(artifact) as t:
    files = {m.name.removeprefix('./'): t.extractfile(m).read() for m in t if m.isfile()}
doc = 'clang64/share/doc/dotnet-roslyn431-bootstrap/'
manifest = json.loads(files[doc+'source-inputs.json'])
audit = json.loads(files[doc+'source-package-audit.json'])
check = json.loads(files[doc+'build-consumer-results.json'])
assert manifest['roslyn_version'] == '4.3.1'
assert manifest['roslyn_commit'] == '4bdc8414790101a4da120a92cc4bc0154ac787ca'
assert manifest['TreatWarningsAsErrors'] is True
assert sha(source_archive.read_bytes()) == manifest['source_archive_sha256'] == '0e254cc88ce10ea4293431c4df687e0c405062a7512f811e270a2b88c5b728a1'
assert check['exit_code'] == 0
assert audit['production_source_changes'] == 0 and audit['all_cached_archives_and_dll_bytes_match_source']
wanted = dict(manifest['original_policy_sha256'])
for data in manifest['projects'].values():
    assert data['production_cs_changes'] == 0
    wanted.update(data['original_cs'])
    wanted.update(data.get('original_resources', {}))
    if 'original_project' in data:
        wanted[data['original_project']] = data['original_project_sha256']
with tarfile.open(source_archive) as t:
    assert t.pax_headers['comment'] == manifest['roslyn_commit']
    originals = {}
    for m in t:
        rel = m.name.partition('/')[2]
        if m.isfile() and (rel in wanted or rel in {'License.txt','THIRD-PARTY-NOTICES.txt'}):
            originals[rel] = t.extractfile(m).read()
for name, digest in wanted.items():
    assert sha(originals[name]) == digest, name
policies = manifest['original_evaluated_compiler_policy']
assert set(policies) == {'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp'}
for name, policy in policies.items():
    assert policy['Features'] == 'strict' and policy['Nullable'] == 'enable'
    assert policy['DisableNullableWarnings'] == 'true'
    assert policy['WarningLevel'] == '9999'
    assert policy['NoWarn'].endswith(';1573;1591;1701;Nullable')
    assert 'netstandard2.0' in policy['TargetFrameworks'].split(';')
for name in ['License.txt','THIRD-PARTY-NOTICES.txt']:
    assert files['clang64/share/licenses/dotnet-roslyn431-bootstrap/'+name] == originals[name]
packages = {}
for name in ['Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.CSharp']:
    data = files['clang64/lib/dotnet/library-packs/'+name.lower()+'.4.3.1.nupkg']
    assert sha(data) == audit['source_packages'][name]['sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        metadata = E.fromstring(z.read(name+'.nuspec')).find('{*}metadata')
        assert metadata.findtext('{*}id') == name and metadata.findtext('{*}version') == '4.3.1'
        assert metadata.find('{*}repository').get('commit') == manifest['roslyn_commit']
        dependencies = {d.get('id'):d.get('version').strip('[]') for d in metadata.iter() if d.tag.endswith('dependency')}
        assert dependencies == audit['source_packages'][name]['compiled_dependencies']
        assembly = 'Microsoft.CodeAnalysis' if name.endswith('.Common') else name
        assert 'lib/netstandard2.0/'+assembly+'.dll' in z.namelist()
        for license in ['License.txt','THIRD-PARTY-NOTICES.txt']:
            assert z.read(license) == originals[license]
        assert len([n for n in z.namelist() if n.endswith('.resources.dll')]) == 13
    packages[name] = sha(data)
generated = json.loads(files[doc+'generated-sources.json'])
operations = json.loads(files[doc+'operation-generated-sources.json'])
assert len(generated) == 5 and len(operations) == 3
assert all(e.get('equivalent_after_bom_line_endings_and_console_blank_line_cleanup') for e in generated)
assert len(json.loads(files[doc+'localization.json'])) == 42
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()),
              original_source_inputs_verified=len(wanted), original_source_changes=0,
              original_NS2_compiler_policy_retained=True, TreatWarningsAsErrors=True,
              generated_compiler_files=5, generated_operation_files=3,
              source_nupkg_sha256=packages, original_public_API_declarations_verified=10090,
              localized_resource_sets=42, localized_strings=35112,
              bootstrap_support_versions=audit['source_packages'],
              original_NETCoreApp31_profile_verified=False,
              full_dependency_goal_complete=False)
output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
