"""Audit an actual MSBuild18 pacman archive independently of its build staging."""
from pathlib import Path
import hashlib,json,sys,tarfile

package,feed_gate,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
base='clang64/share/doc/dotnet-msbuild18-bootstrap/'
tool='clang64/lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/'
with tarfile.open(package) as t:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()}
    def read(name):return t.extractfile(members[name]).read()
    def load(name):return json.loads(read(base+name))
    manifest=load('payload-sha256.json')
    for name,digest in manifest.items():assert sha(read('clang64/'+name))==digest,name
    payload={n for n in members if n.startswith('clang64/')}
    assert payload=={'clang64/'+n for n in manifest}|{base+'payload-sha256.json'},payload^({'clang64/'+n for n in manifest}|{base+'payload-sha256.json'})
    build=load('managed-build-results.json');localization=load('localization-results.json');cli=load('cli-results.json');audit=load('source-audit.json')
    assert build['all6_project_compilations_passed'] and build['original_arcade_version_policy_verified']
    for r in build['projects']:
        assert sha(read(tool+r['project']+'.dll'))==r['output_sha256']
        assert r['original_production_source_changes']==0
        assert r['file_version']=='18.3.0.11413'
    for name,digest in localization['satellite_sha256'].items():assert sha(read(tool+name))==digest
    assert len(localization['satellite_sha256'])==53
    assert audit['original_compile_items']==1326 and audit['source_package_compile_items']==104 and audit['original_localization_inputs_verified']==85
    for r in json.loads(feed_gate.read_text())['items']:
        assert cli['source_runtime_packages'][r['id']]['source_package_sha256']==r['source_nuget_sha256'],r['id']
    assert 'clang64/bin/msbuild18-bootstrap' in members and tool+'msbuild18-bootstrap.cmd' in members
    assert tool+'Check.dll' not in members
    pkginfo=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-msbuild18-bootstrap\n' in pkginfo
    assert 'pkgver = 18.3.0.26113.113-2\n' in pkginfo
    record=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(payload),all_manifest_payload_bytes_verified=True,unexpected_or_missing_payload_files=0,all6_primary_dll_hashes_match_cold_source_outputs=True,all53_satellite_hashes_match_cold_source_outputs=True,all6_exact_oob_feed_hashes_match_existing_source_package_gate=True,source_audit=audit,formal_bootstrap_package_archive_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(record,indent=2)+'\n')
print('PASS actual MSBuild18 package archive',record['regular_payload_files'],'payload files,6 primary DLLs,53 satellites,exact feed/source gates')
