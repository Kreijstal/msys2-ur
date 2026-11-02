"""Verify final Framework16 source package and the explicit NS2 dependency port."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,archive,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())=='04907cbf4ade0101998006e955d7c5ca567e19342340ee71fcd36612158c6726'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-msbuild16-framework-bootstrap/'
record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==record['source_commit']=='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0'
    expected=set(record['original_file_sha256']);originals={}
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and rel in expected:originals[rel]=t.extractfile(m).read()
assert {n:sha(v) for n,v in originals.items()}==record['original_file_sha256']
assert record['production_source_changes']==0 and audit['production_source_changes']==0
assert record['compiled_framework']=='netstandard2.0' and not record['NET472_profile_built']
assert record['pruned_unused_NS2_package_references']=={'System.Runtime.Serialization.Primitives':'4.1.1','System.Threading.Thread':'4.0.0'}
assert audit['original_NS2_feature_guards'] and audit['exact_source_reference_archives_and_DLL_bytes']
assert checks['original_public_API_entries']==743 and checks['original_runtime_reference_table_equal']
assert checks['fresh_NS2_and_NET8_NuGet_consumers'] and checks['source_input_DLL_bytes_verified']
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
provenance=json.loads(files[doc+'inputs/published-api-provenance.json'])
assert sha(files[doc+'inputs/framework16-published-api.json'])==provenance['baseline_sha256']
baseline=json.loads(files[doc+'inputs/framework16-published-api.json']);assert len(baseline['api'])==743
assert baseline['references']==['netstandard, Version=2.0.0.0, Culture=neutral, PublicKeyToken=cc7b13ffcd2ddd51']
assert not provenance['published_assemblies_executed_or_used_as_compiler_references']
package=files['clang64/lib/dotnet/library-packs/microsoft.build.framework.16.0.461.nupkg'];assert sha(package)==audit['package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
    md=E.fromstring(z.read('Microsoft.Build.Framework.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='Microsoft.Build.Framework' and md.findtext('{*}version')=='16.0.461'
    assert not any(e.tag.rsplit('}',1)[-1]=='dependency' for e in md.iter())
    assert md.find('{*}repository').get('commit')==record['source_commit']
    assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/netstandard2.0/Microsoft.Build.Framework.dll']
    for name in ['LICENSE','THIRDPARTYNOTICES.txt']:
        assert z.read(name)==originals[name]
        assert files['clang64/share/licenses/dotnet-msbuild16-framework-bootstrap/'+name]==originals[name]
for name in ['README.md','check-framework.py','inputs/Api.cs','inputs/FrameworkCheck.cs','inputs/framework16-published-api.json','inputs/published-api-provenance.json']:
    assert files[doc+name]==(Path('mingw-w64-dotnet-msbuild16-framework-bootstrap')/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),nupkg_sha256=sha(package),source_commit=record['source_commit'],original_source_files_verified=len(originals),original_CSharp_inputs=audit['original_CSharp_inputs'],production_source_changes=0,original_NS2_feature_guards_and_public_key=True,original_public_API_entries=743,original_runtime_assembly_reference_table_equal=True,pruned_unused_NS2_package_references=record['pruned_unused_NS2_package_references'],source_csc44_original_CSharp_inputs=11,NET472_profile_built=False,original_Arcade_Nerdbank_toolchain_replayed=False,payload_sha256={n:sha(v) for n,v in files.items() if n.startswith('clang64/')},full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
