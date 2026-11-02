"""Independently inspect actual SDK10 support package bytes and immutable VMR sources."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
package,snapshot,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes())=='5a13eccf58c85316c3282bf65de3e53e1adc46f254cac3fc46f0ba7118e3e8d3'
doc='clang64/share/doc/dotnet-sdk10-support-bootstrap/'
with tarfile.open(package) as t,tarfile.open(snapshot) as source:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()};original={m.name:m for m in source.getmembers() if m.isfile()}
    def read(n):return t.extractfile(members[n]).read()
    manifest=json.loads(read(doc+'payload-sha256.json'));build=json.loads(read(doc+'build-results.json'));audit=json.loads(read(doc+'source-audit.json'));api=json.loads(read(doc+'api-results.json'))
    vmr=json.loads(source.extractfile(original['vmr-source-inputs.json']).read());snapshot_manifest=json.loads(source.extractfile(original['snapshot-sha256.json']).read())
    for rel,h in snapshot_manifest.items():assert sha(source.extractfile(original[rel]).read())==h,rel
    for rel,h in manifest.items():assert sha(read('clang64/'+rel))==h,rel
    payload={n for n in members if n.startswith('clang64/')};assert payload=={'clang64/'+rel for rel in manifest}|{doc+'payload-sha256.json'}
    assert audit['original_vmr_compile_inputs']==133 and len(build['projects'])==3
    archives=[];count=0
    for r in build['projects']:
        assert r['original_framework']=='net10.0' and r['original_production_source_changes']==0
        for kind in ['original_source_sha256','original_resource_sha256']:
            for rel,h in r[kind].items():assert sha(source.extractfile(original['runtime/'+rel]).read())==h==vmr['original_vmr_files'][rel]['sha256'],rel
        count+=len(r['original_source_sha256']);name=r['assembly'];version=r['version'];path='clang64/lib/dotnet/library-packs/'+name.lower()+'.'+version+'.nupkg'
        with zipfile.ZipFile(io.BytesIO(read(path))) as z:
            meta=E.fromstring(z.read(name+'.nuspec'));assert meta.findtext('./metadata/id')==name and meta.findtext('./metadata/version')==version
            group=meta.find('./metadata/dependencies/group');assert group.get('targetFramework')=='net10.0' and len(group)==0
            assert meta.find('./metadata/repository').get('commit')=='44525024595742ebe09023abe709df51de65009b'
            for ext,h in r['output_sha256'].items():assert sha(z.read('lib/net10.0/'+name+'.'+ext))==h
        archives.append(dict(id=name,version=version,sha256=sha(read(path)),assembly_version=r['assembly_version'],file_version=r['file_version']))
    assert count==133
    entries=0
    for r in api['projects'].values():assert r['exit_code']==0 and r['comparison']['total_differences']==0 and not r['comparison']['nullable_annotation_differences'];entries+=r['comparison']['expected_entries']
    assert entries==257
    info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-sdk10-support-bootstrap\n' in info and 'pkgver = 10.0.2.25612.105-1\n' in info
report=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(payload),original_vmr_source_files_verified=len(vmr['original_vmr_files']),original_compiler_inputs=133,strict_original_reference_contract_entries=257,missing_extra_changed_and_nullable_differences=0,all_payload_and_source_archive_bytes_verified=True,three_original_NET10_archives_verified=archives,source_snapshot_sha256=sha(snapshot.read_bytes()),full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS actual SDK10 support package,133 original VMR sources,257 exact contract entries and three original NET10 archives')
