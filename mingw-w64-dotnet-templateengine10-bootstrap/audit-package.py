"""Audit final TemplateEngine archives, original VMR inputs and the preserved failed gate."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,snapshot,output=(Path(p).resolve() for p in sys.argv[1:])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes())=='e78c80f2a710a26157d7cc95ee62e1dae48cbaa40c3a70d7472c29b461f4cbbb'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-templateengine10-bootstrap/'
read=lambda name:json.loads(files[doc+name])
manifest=read('payload-sha256.json');build=read('build-results.json');archives=read('archives.json');audit=read('source-audit.json');models=read('evaluated-projects.json');localization=read('localization-results.json');runtime=read('runtime-API-results.json');baseline=read('original-API-failure-results.json')
for rel,expected in manifest.items():assert sha(files['clang64/'+rel])==expected,rel
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
assert len(build['projects'])==len(archives)==7
assert audit['all_original_VMR_snapshot_files_verified']==1891 and audit['original_compile_items']==483
assert audit['original_production_source_changes']==0 and audit['strict_CPM_warning_policy_passed']
assert not audit['strict_original_API_baseline_passed']
assert runtime['strict_API_baseline_exit_code']==1 and runtime['strict_API_baseline_passed'] is False
assert baseline['strict_API_baseline_exit_code']==1 and baseline['strict_API_baseline_passed'] is False and baseline['unchanged_original_missing_entries']==2
assert runtime['owned_TemplateEngine_scan_generation_dryrun_search_json_and_cancellation_passed'] and runtime['strict_CPM_restore_policy_passed']
assert sum(r['expected_entries'] for r in runtime['API_reports'].values())==1986 and sum(len(r['missing']) for r in runtime['API_reports'].values())==2
assert all(c['exit_code']==(1 if i==1 else 0) for i,c in enumerate(runtime['commands']))
resources=read('resource-results.json');assert resources['exact_values']==2268 and resources['satellite_assemblies']==65 and resources['portable_pdb_associations']==7
probe=read('additional-public-api-analyzer-probe.json');assert len(probe['projects'])==6 and all(r['exit_code']==0 for r in probe['projects']) and probe['additional_opt_in_probe']
original_inputs={}
for record in build['projects']:
    assert record['original_production_source_changes']==0 and record['original_target']=='net10.0'
    assert record['original_TreatWarningsAsErrors']=='true' and record['original_EnableAnalyzers']=='false'
    assert record['package_version']=='10.0.200-preview.26113.113' and record['assembly_version']=='10.0.200.0' and record['file_version']=='10.2.26.11413'
    original_inputs.update(record['original_source_sha256']);original_inputs.update({n:r['sha256'] for n,r in record['original_resources'].items()})
with tarfile.open(snapshot) as t:
    vmr=json.load(t.extractfile('source-inputs.json'))
    for rel,expected in original_inputs.items():assert sha(t.extractfile('templating/'+rel).read())==expected==vmr['files'][rel]['sha256'],rel
binary='clang64/lib/dotnet10/library-packs/templateengine-10.0.200-preview.26113.113-net10-bootstrap/bin/'
for record in build['projects']:
    name=record['assembly'];archive=archives[name];data=files['clang64/'+archive['archive']];assert sha(data)==archive['sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert {n:sha(z.read(n)) for n in z.namelist()}==archive['members']
        meta=E.fromstring(z.read(name+'.nuspec')).find('metadata')
        assert meta.findtext('id')==name and meta.findtext('version')=='10.0.200-preview.26113.113'
        assert meta.find('repository').get('commit')=='05d9490471fb4b10d7ef4faa32c423e1b5adcaee'
        group=meta.find('dependencies/group');assert group.get('targetFramework')=='net10.0'
        expected_edges={r['assembly']:'[10.0.200-preview.26113.113]' for r in record['original_project_edges'] if r['metadata'].get('ReferenceOutputAssembly','true').lower()!='false'}
        central={p['identity']:p['metadata']['Version'] for p in models[name]['items']['PackageVersion'] if p['metadata'].get('Version')}
        expected_edges.update({p['identity']:central[p['identity']] for p in models[name]['items']['PackageReference'] if p['metadata'].get('PrivateAssets','').lower()!='all'})
        assert {e.get('id'):e.get('version') for e in group}==expected_edges
        for ext,expected in record['output_sha256'].items():assert sha(z.read('lib/net10.0/'+name+'.'+ext))==sha(files[binary+name+'.'+ext])==expected
for rel,expected in localization['satellite_sha256'].items():assert sha(files[binary+rel])==expected
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),payload_files_verified=len(manifest),NuGet_archives=7,original_source_compile_items=483,unique_original_compile_inputs=477,original_VMR_files_verified=1891,original_production_source_changes=0,original_NET10_framework_warning_nullable_key_and_version_policies_preserved=True,original_central_dependency_versions_and_package_edges_verified=True,original_1986_entry_API_baseline_still_failed=True,strict_all_seven_API_baseline_passed=False,strict_API_exit_code=1,unchanged_original_missing_API_entries=2,additional_source_public_API_analyzer_projects_passed=6,neutral_and_localized_resource_sets=70,resource_values=2268,satellites=65,portable_PDBs=7,owned_folder_and_local_NuGet_template_install_generate_uninstall_passed=True,other_original_framework_profiles_built=False,full_original_SDK_pruning_integration_verified=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
