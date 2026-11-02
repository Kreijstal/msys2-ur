"""Check the final source reference pack and its linked strict metadata gates."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
import tarfile

artifact,sbrp,corefx,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
pins=[(sbrp,'2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79','5aeee2738338530a92d7f6caa2c7d5f569fed3c4',''),(corefx,'986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601','9688ddbb62c04189cac4c4a06e31e93377dccd41','corefx/')]
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-legacy-ns13-contracts-bootstrap/';pack='clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/'
record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-check-results.json']);build=json.loads(files[doc+'build-results.json'])
originals={};license_originals={}
for archive,digest,commit,prefix in pins:
    assert sha(archive.read_bytes())==digest
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment']==commit
        for m in t:
            name=prefix+m.name.partition('/')[2]
            if m.isfile() and name in {'LICENSE.txt','corefx/LICENSE','corefx/THIRD-PARTY-NOTICES'}:license_originals[name]=t.extractfile(m).read()
            if m.isfile() and name in record['original_file_sha256']:originals[name]=t.extractfile(m).read()
assert {n:sha(b) for n,b in originals.items()}==record['original_file_sha256']
assert record['production_source_changes']==audit['production_source_changes']==4
assert record['original_source_files_modified_in_place']==audit['original_source_files_modified_in_place']==0
assert audit['unchanged_contract_source_variants']==29 and audit['ported_contract_variants']==4
assert audit['all_compile_inputs_and_exact_reference_DLL_bytes_verified'] and audit['warnings_as_errors'] and audit['reference_only']
assert len(record['libraries'])==len(build)==33 and len(record['root_contracts'])==16
assert checks['contract_count']==16 and checks['build_contract_variant_count']==33
assert checks['original_public_API_entries']==7430 and checks['build_matrix_original_public_API_entries']==14637
assert checks['original_identity_and_dependency_reference_sets_equal'] and checks['original_reference_only_markers']
assert checks['original_COM_struct_layout_and_field_offsets_verified'] and checks['consumer_compiler_references_only_source_legacy_contracts'] and checks['consumer_source_NET8_runtime_host']
assert checks['original_public_Conditional_attributes_verified'] and checks['public_Conditional_attribute_entries']==53 and checks['release_Debug_calls_omitted']
assert checks['Dataflow_lower_contract_typed_consumer_passed']
assert checks['Dataflow_lower_contract_consumer_references'] and all('/4.0.0.0/' in k for k in checks['Dataflow_lower_contract_consumer_references'])
assert all(c['exit_code']==0 for c in checks['commands'])
recipe=Path('mingw-w64-dotnet-legacy-ns13-contracts-bootstrap')
interop=record['libraries']['System.Runtime.InteropServices/4.0.20.0']
ported=runpy.run_path(str(recipe/'port-interop.py'))['port'](originals[interop['source']].decode('utf-8-sig'),originals[interop['port_original_CoreFX_source']].decode('utf-8-sig'))
assert sha(ported.encode())==record['generated_source_sha256']['Interop.Ported.cs']
header=originals['src/referencePackages/src/system.diagnostics.tools/4.3.0/ref/netstandard1.0/System.Diagnostics.Tools.cs'].decode('utf-8-sig').split('namespace System.CodeDom.Compiler')[0]
assert sha(header.encode())==record['generated_source_sha256']['System.Diagnostics.Tools.AssemblyInfo.cs']
assert sha(header.replace('System.Diagnostics.Tools','System.Diagnostics.Contracts').encode())==record['generated_source_sha256']['System.Diagnostics.Contracts.AssemblyInfo.cs']
debug_header=originals['src/referencePackages/src/system.diagnostics.debug/4.3.0/ref/netstandard1.3/System.Diagnostics.Debug.cs'].decode('utf-8-sig').split('namespace System.Diagnostics')[0]
assert sha(debug_header.encode())==record['generated_source_sha256']['System.Diagnostics.Debug.AssemblyInfo.cs']
debug=record['libraries']['System.Diagnostics.Debug/4.0.0.0']
debug_port=runpy.run_path(str(recipe/'port-debug.py'))['port'](originals[debug['source']].decode('utf-8-sig'),originals[debug['port_original_CoreFX_source']].decode('utf-8-sig'))
assert sha(debug_port.encode())==record['generated_source_sha256']['Debug.NS10.Ported.cs']
ports=runpy.run_path(str(recipe/'port-additional.py'))
item=record['libraries']['System.Runtime.Serialization.Primitives/4.0.0.0']
assert sha(ports['serialization'](originals[item['source']].decode('utf-8-sig'),originals[item['port_original_CoreFX_source']].decode('utf-8-sig')).encode())==record['generated_source_sha256'][item['generated_port_source']]
item=record['libraries']['System.ObjectModel/4.0.0.0']
assert sha(ports['object_model'](originals[item['source']].decode('utf-8-sig')).encode())==record['generated_source_sha256'][item['generated_port_source']]
expected_dlls=set()
for key,item in record['libraries'].items():
    path=pack+'contracts/'+key+'/'+item['name']+'.dll';expected_dlls.add(path)
    assert sha(files[path])==audit['output_sha256'][key]==build[key]['output_sha256']
    assert build[key]['exit_code']==0 and build[key]['reference_only']
for name,key in record['root_contracts'].items():
    path=pack+'ref/'+name+'.dll';expected_dlls.add(path)
    assert files[path]==files[pack+'contracts/'+key+'/'+name+'.dll']
assert {n for n in files if n.endswith('.dll')}==expected_dlls
assert not any(n.endswith('.nupkg') for n in files)
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
    verified=set()
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and rel in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(m).read())==compiler['original_csc_compile_items'][rel];verified.add(rel)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
for name in ['README.md','check.py','inputs/Api.cs','inputs/Check.cs','inputs/Probe.cs','inputs/published-metadata.json','inputs/published-build-matrix.json','inputs/published-provenance.json','inputs/build-matrix-provenance.json','inputs/interop-layouts.json','inputs/conditional-attributes.json']:assert files[doc+name]==(recipe/name).read_bytes()
for name,origin in [('SBRP-LICENSE.txt','LICENSE.txt'),('CoreFX-LICENSE','corefx/LICENSE'),('CoreFX-THIRD-PARTY-NOTICES','corefx/THIRD-PARTY-NOTICES')]:assert files['clang64/share/licenses/dotnet-legacy-ns13-contracts-bootstrap/'+name]==license_originals[origin]
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),original_source_files_verified=len(originals),root_reference_contracts=16,build_contract_variants=33,root_public_API_entries=7430,build_matrix_public_API_entries=14637,original_reference_identities_equal=True,original_COM_layout_and_field_offsets_verified=True,original_public_Conditional_attribute_entries=53,Release_consumer_Debug_Fail_omitted_from_IL=True,unchanged_contract_source_variants=29,ported_Interop_variant=1,ported_Debug_NS10_variant=1,ported_Serialization_NS10_variant=1,ported_ObjectModel_NS10_variant=1,original_source_files_modified_in_place=0,reference_only=True,NuGet_runtime_archives_installed=0,original_csc44_source_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},full_NETStandard13_runtime_package_closure_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
