"""Verify final source-only packages against original Git inputs and release content hashes."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact,source_archive,version,out=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),sys.argv[3],Path(sys.argv[4]).resolve()
sha=lambda b:hashlib.sha256(b).hexdigest();major=version.split('.')[0];doc='clang64/share/doc/dotnet-wcwidth'+major+'-sources/'
with tarfile.open(artifact) as t:files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
read=lambda n:json.loads(files[doc+n]);manifest=read('payload-sha256.json');r=read('source-results.json');checked=read('producer-check-results.json');contract=read('original-source-contracts.json')[version]
for rel,h in manifest.items():assert sha(files['clang64/'+rel])==h,rel
assert {n for n in files if n.startswith('clang64/')}=={'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
assert r['version']==version and r['original_source_changes']==0 and checked['version']==version
assert r['original_source_frameworks']==contract['original_source_frameworks']
assert r['content_file_sha256']==contract['content_files']
assert sha(source_archive.read_bytes())==r['source_archive_sha256']==contract['source_archive_sha256']
with tarfile.open(source_archive) as t:
    prefix='wcwidth-'+r['source_commit']+'/'
    for rel,h in r['source_files_sha256'].items():assert sha(t.extractfile(prefix+rel).read())==h,rel
    for rel,h in r['original_production_source_sha256'].items():assert sha(t.extractfile(prefix+'src/Wcwidth/'+rel).read())==h,rel
for n,data in files.items():
    if n.startswith(doc+'validation-source/'):
        rel=n[len(doc+'validation-source/'):];assert sha(data)==r['source_files_sha256'][rel]
package_path='clang64/lib/dotnet/library-packs/wcwidth.sources.'+version+'.nupkg';data=files[package_path];assert sha(data)==r['archive_sha256']
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert {n:sha(z.read(n)) for n in z.namelist()}==r['archive_members']
    assert not any(n.lower().endswith(('.dll','.exe','.pdb')) for n in z.namelist())
    md=E.fromstring(z.read('Wcwidth.Sources.nuspec')).find('metadata');assert md.findtext('id')=='Wcwidth.Sources' and md.findtext('version')==version
    assert md.find('repository').get('commit')==r['source_commit']
    assert {e.get('include') for e in md.find('contentFiles')}==set(contract['content_files'])
    assert all(e.get('buildAction')=='Compile' for e in md.find('contentFiles'))
    for n,h in contract['content_files'].items():assert sha(z.read(n))==h
assert all(c['exit_code']==0 for c in checked['commands'])
assert checked['upstream_Fact_methods_executed']==(10 if version=='2.0.0' else 24)
assert checked['actual_NETStandard2_consumer_profiles']==['public','internal'] and checked['assertion_negative_control_rejected']
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),version=version,source_commit=r['source_commit'],source_archive_sha256=sha(source_archive.read_bytes()),original_source_files_verified=len(r['source_files_sha256']),production_source_files=len(r['original_production_source_sha256']),original_source_changes=0,payload_files_verified=len(manifest),original_content_file_entries_verified=len(contract['content_files']),original_source_frameworks=contract['original_source_frameworks'],all_source_bytes_equal_original_release=True,contains_no_prebuilt_or_produced_binary_assets=True,unchanged_upstream_Fact_methods_executed=checked['upstream_Fact_methods_executed'],actual_NETStandard2_public_and_internal_consumers_executed=True,original_MinVer_NuGetizer_analyzers_toolchain_replayed=False,all_original_runtime_hosts_tested=False,full_dependency_goal_complete=False)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
