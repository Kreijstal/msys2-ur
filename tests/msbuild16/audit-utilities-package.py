"""Verify final Utilities16 source package, original dependencies and linked checks."""
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
doc='clang64/share/doc/dotnet-msbuild16-utilities-bootstrap/';record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json'])
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==record['source_commit']=='6ff56ef63c3a1c9785d42fe2564d904ebd225ea0';originals={}
    for member in t:
        name=member.name.partition('/')[2]
        if member.isfile() and name in record['original_file_sha256']:originals[name]=t.extractfile(member).read()
assert {n:sha(b) for n,b in originals.items()}==record['original_file_sha256']
assert record['production_CSharp_changes']==audit['production_CSharp_changes']==0 and record['compiled_framework']=='netstandard2.0'
assert audit['original_NS2_feature_guards'] and audit['all_actual_reference_DLL_bytes_verified_against_source_archives']
assert checks['original_public_API_entries']==487 and checks['source_resource_strings_verified']==110
assert checks['original_runtime_dependency_identity_sets_equal'] and checks['isolated_original_implementations_executed'] and checks['exact_cached_candidate_NuGet_archive_verified']
assert all(c['exit_code']==0 for c in checks['commands'])
versions={'Microsoft.Build.Framework':'16.0.461','System.Collections.Immutable':'1.5.0','Microsoft.Win32.Registry':'4.3.0','System.Text.Encoding.CodePages':'4.0.1'}
assert record['exact_original_dependency_versions']==audit['exact_original_dependency_versions']==versions
package=files['clang64/lib/dotnet/library-packs/microsoft.build.utilities.core.16.0.461.nupkg'];assert sha(package)==audit['package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
    metadata=E.fromstring(z.read('Microsoft.Build.Utilities.Core.nuspec')).find('{*}metadata');assert metadata.findtext('{*}id')=='Microsoft.Build.Utilities.Core' and metadata.findtext('{*}version')=='16.0.461'
    assert {e.get('id'):e.get('version') for e in metadata.findall('.//{*}dependency')}=={n:'['+v+']' for n,v in versions.items()}
    assert metadata.find('{*}repository').get('commit')==record['source_commit']
    assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/netstandard2.0/Microsoft.Build.Utilities.Core.dll']
    assert sha(z.read('lib/netstandard2.0/Microsoft.Build.Utilities.Core.dll'))==checks['consumer_DLL_sha256']['Microsoft.Build.Utilities.Core']
    for license in ['LICENSE','THIRDPARTYNOTICES.txt']:
        assert z.read(license)==originals[license]
        assert files['clang64/share/licenses/dotnet-msbuild16-utilities-bootstrap/'+license]==originals[license]
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a';verified=set()
    for member in t:
        name=member.name.partition('/')[2]
        if member.isfile() and name in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(member).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
recipe=Path('mingw-w64-dotnet-msbuild16-utilities-bootstrap')
for name in ['README.md','check-utilities.py','inputs/Api.cs','inputs/UtilitiesBridge.cs','inputs/UtilitiesCheck.cs','inputs/utilities16-published-metadata.json']:assert files[doc+name]==(recipe/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),nupkg_sha256=sha(package),source_commit=record['source_commit'],original_source_files_verified=len(originals),original_CSharp_inputs=audit['original_CSharp_inputs'],production_CSharp_changes=0,original_NS2_feature_policy=True,original_public_API_entries=487,original_resource_strings_verified=110,original_runtime_dependency_identity_sets_equal=True,exact_original_dependency_versions=versions,isolated_task_item_command_line_logging_and_ToolTask_checks=True,source_csc44_original_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},NET472_profile_built=False,original_Nerdbank_toolchain_replayed=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
