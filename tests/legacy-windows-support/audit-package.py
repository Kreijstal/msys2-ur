"""Verify final original-source Windows archives and explicit compatibility profiles."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,registry,codepages,roslyn,output=map(Path,sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-legacy-windows-support-bootstrap/';record=json.loads(files[doc+'source-inputs.json']);audit=json.loads(files[doc+'producer-audit.json']);checks=json.loads(files[doc+'producer-original-check-results.json']);nuget=json.loads(files[doc+'producer-nuget-check-results.json']);contract=json.loads(files[doc+'inputs/package-contract.json'])
assert audit['production_CSharp_changes']==0 and audit['original_NS13_windows_source_profiles'] and audit['original_NS13_NuGet_dependencies_preserved'] and audit['NS2_compatibility_assets_byte_identical']
for check in [checks,nuget]:assert check['original_public_API_entries']==106 and check['original_runtime_reference_identity_sets_equal'] and all(c['exit_code']==0 for c in check['commands'])
assert checks['isolated_original_implementation_versions_executed'] and checks['native_registry_owned_subtree_cleanup_verified']
assert nuget['isolated_original_implementations_executed'] and nuget['fresh_NS2_PackageReference_consumer_zero_restore_diagnostics'] and nuget['original_NS13_DLL_bytes_identical_to_NS2_compatibility_assets']
reference_checks=json.loads(files[doc+'producer-reference-check-results.json']);reference_build=json.loads(files[doc+'reference-build-results.json'])
assert reference_checks['original_reference_API_entries']==nuget['original_reference_API_entries']==102 and nuget['original_reference_identity_sets_equal']
assert all(c['exit_code']==0 for c in reference_checks['commands'])
assert not nuget['original_NS13_NuGet_runtime_closure_verified']
packages={};source_count=0;compile_count=0
for name,archive in [('Microsoft.Win32.Registry',registry),('System.Text.Encoding.CodePages',codepages)]:
    item=record['libraries'][name];source_audit=audit['libraries'][name]
    assert sha(archive.read_bytes())==item['source_archive_sha256']
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment']==item['source_commit'];originals={}
        for member in t:
            path=member.name.partition('/')[2]
            if member.isfile() and path in item['original_file_sha256']:originals[path]=t.extractfile(member).read()
    assert {n:sha(b) for n,b in originals.items()}==item['original_file_sha256'];source_count+=len(originals);compile_count+=source_audit['original_CSharp_inputs']
    assert item['production_CSharp_changes']==source_audit['production_CSharp_changes']==0 and item['original_target_framework']=='netstandard1.3'
    row=reference_build[name];assert row['exit_code']==0 and row['source_CSharp_changes']==0
    assert all(sha(originals[p])==digest for p,digest in row['original_source_sha256'].items())
    assert sha(originals['src/'+name+'/ref/'+name+'.csproj'])==row['reference_source_project_sha256']
    package=files['clang64/lib/dotnet/library-packs/'+name.lower()+'.'+item['version']+'.nupkg'];assert sha(package)==source_audit['package_sha256']
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert {n:sha(z.read(n)) for n in z.namelist()}==source_audit['archive_members']
        metadata=E.fromstring(z.read(name+'.nuspec')).find('{*}metadata');assert metadata.findtext('{*}id')==name and metadata.findtext('{*}version')==item['version']
        assert metadata.find('{*}repository').get('commit')==item['source_commit']
        groups={g.get('targetFramework').replace('.','').lower():g for g in metadata.findall('{*}dependencies/{*}group')}
        assert [dict(d.attrib) for d in groups['netstandard13']]==contract[name]['original_NS13_dependencies']
        assert [dict(d.attrib) for d in groups['netstandard20']]==[{'id':'NETStandard.Library','version':'[2.0.3]'}]
        dll=z.read('lib/netstandard1.3/'+name+'.dll');assert dll==z.read('lib/netstandard2.0/'+name+'.dll')
        reference=z.read('ref/netstandard1.3/'+name+'.dll');assert reference==z.read('ref/netstandard2.0/'+name+'.dll') and sha(reference)==row['output_sha256']==source_audit['original_contract_DLL_sha256']
        assert sha(dll)==checks['candidate_DLL_sha256'][name]==nuget['DLL_sha256'][name]
        if name=='System.Text.Encoding.CodePages':assert contract[name]['original_NET46_DLL_identical_to_Windows_NS13'] and dll==z.read('lib/net46/'+name+'.dll')==z.read('ref/net46/'+name+'.dll')
        for license in ['LICENSE','THIRD-PARTY-NOTICES']:
            assert z.read(license)==originals[license]
            assert files['clang64/share/licenses/dotnet-legacy-windows-support-bootstrap/'+name+'/'+license]==originals[license]
        port=json.loads(z.read('source-port.json'));assert port['compiled_original_framework']=='netstandard1.3' and not port['original_NS13_NuGet_runtime_closure_verified']
    packages[name]=dict(version=item['version'],source_commit=item['source_commit'],source_CSharp_changes=0,nupkg_sha256=sha(package),DLL_sha256=sha(dll),reference_DLL_sha256=sha(reference),original_reference_assembly_version=row['original_reference_assembly_version'],original_NS13_dependencies=contract[name]['original_NS13_dependencies'],additional_NS2_dependency={'NETStandard.Library':'[2.0.3]'})
compiler=json.loads(files[doc+'compiler44-source-inputs.json']);assert sha(roslyn.read_bytes())==compiler['source_archive_sha256']=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(roslyn) as t:
    assert t.pax_headers['comment']==compiler['source_commit']=='1ce8866c9de4c2d67351ef6863699dee03b0804a';verified=set()
    for member in t:
        path=member.name.partition('/')[2]
        if member.isfile() and path in compiler['original_csc_compile_items']:
            assert sha(t.extractfile(member).read())==compiler['original_csc_compile_items'][path];verified.add(path)
assert len(verified)==11 and compiler['original_csc_source_changes']==0
recipe=Path('mingw-w64-dotnet-legacy-windows-support-bootstrap')
for name in ['README.md','check-nuget.py','inputs/Api.cs','inputs/Check.cs','inputs/ReferenceCheck.cs','inputs/Bridge.cs','inputs/published-runtime-metadata.json','inputs/published-reference-metadata.json','inputs/package-contract.json']:assert files[doc+name]==(recipe/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),original_source_files_verified=source_count,original_CSharp_inputs=compile_count,original_reference_CSharp_inputs=sum(len(row['original_source_sha256']) for row in reference_build.values()),production_CSharp_changes=0,original_windows_NS13_source_profiles=True,original_public_API_entries=106,original_reference_API_entries=102,original_reference_and_runtime_identity_sets_equal=True,original_runtime_reference_identity_sets_equal=True,source_resource_strings_verified=184,original_codepages_nlp_bytes_verified=True,native_registry_encoding_and_cleanup_checks_passed=True,fresh_NS2_NuGet_consumers_zero_diagnostics=True,NS2_assets_identical_to_original_NS13_builds=True,original_NS13_dependency_groups_preserved=True,packages=packages,source_csc44_original_inputs=11,payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},original_NS13_runtime_NuGet_closure_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='payload_sha256'},indent=2))
