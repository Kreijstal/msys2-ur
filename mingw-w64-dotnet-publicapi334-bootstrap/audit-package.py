"""Independently audit the final package payload and its production validation gates."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact, original_archive, output = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda data: hashlib.sha256(data).hexdigest()
with tarfile.open(artifact) as package:
    files = {m.name.removeprefix('./'): package.extractfile(m).read() for m in package if m.isfile()}
doc = 'clang64/share/doc/dotnet-publicapi334-bootstrap/'
read = lambda name:json.loads(files[doc+name])
manifest = read('payload-sha256.json')
for rel, expected in manifest.items():assert sha(files['clang64/'+rel]) == expected, rel
assert {n for n in files if n.startswith('clang64/')} == {'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
build = read('build-results.json')
assert build['compiler_warnings_as_errors'] and build['original_NETStandard2_profiles_preserved']
ports = {}
original_sources = {}
for record in build['projects'].values():
    assert record['original_framework'] == 'netstandard2.0'
    assert record['original_source_Roslyn_capability_guards_preserved']
    original_sources.update(record['sources'])
    original_sources.update(record['original_imports'])
    original_sources.update(record['resource_files'])
    ports.update(record['source_ports'])
assert sha(original_archive.read_bytes()) == '49a992347546aef48cb31673b294bd1b10c30e68bbb53be61d411bb0d7219e1e'
with tarfile.open(original_archive) as archive:
    prefix = 'roslyn-analyzers-22ea6422f85b05ca0793cc3b76375487be407f5d/'
    for rel, expected in original_sources.items():assert sha(archive.extractfile(prefix+rel).read()) == expected, rel
source_audit = read('source-audit.json')
assert source_audit['original_snapshot_files_verified'] == 606
assert source_audit['original_source_inputs_verified'] == 123
assert source_audit['production_compiler_warnings_as_errors'] and len(ports) == 13
assert source_audit['original_package_policy_text_assets_verified'] == 102
metadata = read('metadata-results.json')
assert all(p['exit_code']==0 and p['comparison']['total_differences']==0 and not p['comparison']['nullable_annotation_differences'] for p in metadata['projects'].values())
assert sum(p['comparison']['expected_entries'] for p in metadata['projects'].values()) == 47
cli = read('cli-results.json');assert len(cli['cases']) == 5 and all(c['exit_code']==c['expected_exit_code'] for c in cli['cases'])
fix = read('codefix-results.json');assert fix['codefix_providers_executed']==3 and fix['document_fix_all_cases']==3
resources = read('resource-results.json');assert resources['exact_values']==812 and resources['satellite_assemblies']==13 and resources['portable_pdb_associations']==2
policy = read('package-config-comparison.json');assert len(policy['files'])==102 and policy['all_text_metadata_equal']
archive = read('archives.json')
with zipfile.ZipFile(io.BytesIO(files['clang64/'+archive['archive']])) as nupkg:
    assert {n:sha(nupkg.read(n)) for n in nupkg.namelist()} == archive['members']
    meta = E.fromstring(nupkg.read('Microsoft.CodeAnalysis.PublicApiAnalyzers.nuspec')).find('metadata')
    assert meta.findtext('id') == 'Microsoft.CodeAnalysis.PublicApiAnalyzers' and meta.findtext('version') == '3.3.4'
    assert meta.find('repository').get('commit') == '22ea6422f85b05ca0793cc3b76375487be407f5d'
    for record in build['projects'].values():
        for ext, expected in record['output_sha256'].items():assert sha(nupkg.read('analyzers/dotnet/'+record['assembly']+'.'+ext)) == expected
report = dict(artifact=artifact.name, artifact_sha256=sha(artifact.read_bytes()), payload_files_verified=len(manifest), original_source_inputs=123, original_snapshot_files_verified=606, explicit_source_port_files=len(ports), compiler_warnings_as_errors=True, strict_CLR_and_nullable_metadata_entries=47, strict_metadata_differences=0, diagnostic_cases=5, codefix_providers=3, document_fix_all_cases=3, neutral_and_localized_resource_sets=14, exact_resource_values=812, satellite_assemblies=13, portable_PDBs=2, regenerated_package_policy_and_documentation_texts_verified=102, NuGet_archive_members=len(archive['members']), original_NS2_and_source_feature_guards_preserved=True, original_Roslyn12_host_compatibility_verified=False, full_original_SDK10_build_verified=False, full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
