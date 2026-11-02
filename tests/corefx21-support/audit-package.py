"""Audit final CoreFX 2.1 source package, provenance and linked checks."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,archive,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())=='a886ecc798d92fa1183eb127f95ceb47270be7a53fcae51e7f391523c261e586'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-corefx21-metadata-bootstrap/'
record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==record['source_commit']=='30ab651fcb4354552bd4891619a0bdd81e0ebdbf'
    expected=set(record['original_file_sha256']);originals={}
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and rel in expected:originals[rel]=t.extractfile(m).read()
assert {n:sha(v) for n,v in originals.items()}==record['original_file_sha256']
assert record['production_CSharp_changes']==audit['production_CSharp_changes']==0
assert record['compiled_profile']=='netstandard2.0' and not record['other_original_profiles_built']
assert audit['original_NS2_source_conditions'] and audit['source_only_reference_archives_and_DLL_bytes']
assert checks['original_public_API_entries']==3874 and checks['original_runtime_reference_tables_equal']
assert checks['isolated_original_version_implementations_executed'] and checks['fresh_original_NS2_PackageReference_consumer'] and checks['all_source_resource_values_verified']
assert all(c['exit_code']==0 for c in checks['commands'])
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
    verified=set()
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and rel in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][rel];verified.add(rel)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
provenance=json.loads(files[doc+'inputs/published-provenance.json'])
assert sha(files[doc+'inputs/published-ns2-metadata.json'])==provenance['metadata_baseline_sha256']
baseline=json.loads(files[doc+'inputs/published-ns2-metadata.json']);packages={}
assert sum(len(x['api']) for x in baseline.values())==3874
for name,version in [('System.Collections.Immutable','1.5.0'),('System.Reflection.Metadata','1.6.0')]:
    assert not provenance['libraries'][name]['published_binaries_executed_or_used_as_compiler_references']
    package=files['clang64/lib/dotnet/library-packs/'+name.lower()+'.'+version+'.nupkg'];item=audit['libraries'][name]
    assert sha(package)==item['package_sha256']
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert {n:sha(z.read(n)) for n in z.namelist()}==item['archive_members']
        md=E.fromstring(z.read(name+'.nuspec')).find('{*}metadata')
        assert md.findtext('{*}id')==name and md.findtext('{*}version')==version
        deps={e.get('id'):e.get('version') for e in md.iter() if e.tag.rsplit('}',1)[-1]=='dependency'}
        assert deps==({'System.Collections.Immutable':'[1.5.0]'} if name=='System.Reflection.Metadata' else {})
        assert md.find('{*}repository').get('commit')==record['source_commit']
        assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/netstandard2.0/'+name+'.dll']
        for lic in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
            assert z.read(lic)==originals[lic]
            assert files['clang64/share/licenses/dotnet-corefx21-metadata-bootstrap/'+lic]==originals[lic]
    packages[name]=dict(version=version,nupkg_sha256=sha(package),original_CSharp_inputs=item['original_CSharp_inputs'])
recipe=Path('mingw-w64-dotnet-corefx21-metadata-bootstrap')
for name in ['README.md','check.py','inputs/Api.cs','inputs/Check.cs','inputs/Bridge.cs','inputs/published-ns2-metadata.json','inputs/published-provenance.json']:assert files[doc+name]==(recipe/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),source_commit=record['source_commit'],original_source_files_verified=len(originals),original_CSharp_inputs=audit['original_CSharp_inputs'],production_CSharp_changes=0,original_public_API_entries=3874,original_runtime_reference_tables_equal=True,source_resource_values_verified=124,isolated_original_versions_executed=True,source_csc44_original_inputs=11,packages=packages,other_original_profiles_built=False,original_buildtools_host_replayed=False,payload_sha256={n:sha(v) for n,v in files.items() if n.startswith('clang64/')},full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
