"""Check final Cecil archive against original source and compiler-source pins."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,cecil_archive,roslyn_archive,output=map(Path,sys.argv[1:])
sha=lambda data:hashlib.sha256(data).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-cecil011-bootstrap/'
record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json'])
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);checks=json.loads(files[doc+'producer-check-results.json'])
assert sha(cecil_archive.read_bytes())==record['source_archive_sha256']=='ef581a6ff59c8c5993f82ec5dadd470d185823e9407846c3ac992e23efdbcad3'
with tarfile.open(cecil_archive) as t:
    assert t.pax_headers['comment']==record['source_commit']=='12da1bf7e0e10278e05eeb23adfc72760bbb6668'
    source={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile()}
for name,digest in record['original_file_sha256'].items():assert sha(source[name])==digest,name
for name,digest in record['excluded_binary_fixture_sha256'].items():assert sha(source[name])==digest,name
assert record['source_changes']==0 and audit['original_production_source_changes']==0
assert sum(len(v['original_cs']) for v in record['projects'].values())==188
assert not record['NET40_profile_built'] and not audit['NET40_profile_built']
assert audit['original_NS2_guards_and_signing_key_retained'] and audit['strict_WAE_probe']
assert sha(roslyn_archive.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
assert compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
with tarfile.open(roslyn_archive) as t:
    assert t.pax_headers['comment']==compiler['source_commit']
    verified=set()
    for m in t:
        name=m.name.partition('/')[2]
        if m.isfile() and name in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][name];verified.add(name)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
assert checks['actual_IL_and_nullable_metadata_rewriting'] and checks['portable_and_embedded_PDB_round_trips']
assert checks['exact_cached_archive_and_copied_DLL_bytes'] and all(c['exit_code']==0 for c in checks['commands'])
baseline=json.loads(files[doc+'inputs/published-ns2-api.json']);provenance=json.loads(files[doc+'inputs/published-api-provenance.json'])
assert sum(map(len,baseline.values()))==3844
assert sha(files[doc+'inputs/published-ns2-api.json'])==provenance['baseline_sha256']
assert not provenance['published_binaries_executed_or_used_as_compiler_references']
package=files['clang64/lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg']
assert sha(package)==audit['package_sha256']
with zipfile.ZipFile(io.BytesIO(package)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==audit['archive_members']
    md=E.fromstring(z.read('Mono.Cecil.nuspec')).find('{*}metadata')
    assert md.findtext('{*}id')=='Mono.Cecil' and md.findtext('{*}version')=='0.11.0'
    assert {n.get('targetFramework') for n in md.find('{*}dependencies')}=={'.NETStandard2.0'}
    assert {n for n in z.namelist() if n.endswith('.dll')}=={'lib/netstandard2.0/'+name+'.dll' for name in baseline}
    assert len([n for n in z.namelist() if n.endswith('.pdb')])==4
    for member,path in [('LICENSE.txt','LICENSE.txt'),('licenses/Microsoft.Cci.Pdb/LICENSE','symbols/pdb/Microsoft.Cci.Pdb/LICENSE')]:assert z.read(member)==source[path]
    for name,data in source.items():
        if name.startswith('symbols/mdb/Mono.CompilerServices.SymbolWriter/') and name.endswith('.cs'):
            assert z.read('licenses/Mono.CompilerServices.SymbolWriter/'+Path(name).name+'.txt')==data
            assert files['clang64/share/licenses/dotnet-cecil011-bootstrap/Mono.CompilerServices.SymbolWriter/'+Path(name).name]==data
assert files['clang64/share/licenses/dotnet-cecil011-bootstrap/LICENSE.txt']==source['LICENSE.txt']
assert files['clang64/share/licenses/dotnet-cecil011-bootstrap/Microsoft.Cci.Pdb/LICENSE']==source['symbols/pdb/Microsoft.Cci.Pdb/LICENSE']
for name in ['README.md','check.py','inputs/Api.cs','inputs/Check.cs','inputs/published-ns2-api.json','inputs/published-api-provenance.json']:
    assert files[doc+name]==(Path('mingw-w64-dotnet-cecil011-bootstrap')/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),nupkg_sha256=sha(package),source_commit=record['source_commit'],source_files_verified=len(record['original_file_sha256']),original_CSharp_inputs=188,production_source_changes=0,excluded_binary_fixtures=len(record['excluded_binary_fixture_sha256']),compiler44_original_cli_inputs_verified=11,original_NS2_library_count=4,original_public_API_entries=3844,strict_metadata_baseline_changed=False,IL_nullable_and_portable_embedded_symbol_checks_passed=True,NET40_profile_built=False,full_native_symbol_fixture_matrix_verified=False,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
