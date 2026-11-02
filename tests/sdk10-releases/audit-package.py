"""Independently inspect Releases implementation and separate original reference-only assets."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
package,snapshot,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(snapshot.read_bytes())=='8d2f0663d6e8d7d8bf478d4e14cf767d250851fe656be92ac26002524b11771d'
doc='clang64/share/doc/dotnet-deployment-releases-bootstrap/';name='Microsoft.Deployment.DotNet.Releases';version='2.0.0-preview.1.25612.105'
with tarfile.open(package) as t,tarfile.open(snapshot) as original:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()};source={m.name:m for m in original.getmembers() if m.isfile()}
    def read(n):return t.extractfile(members[n]).read()
    manifest=json.loads(read(doc+'payload-sha256.json'));build=json.loads(read(doc+'build-results.json'));refs=json.loads(read(doc+'reference-build-results.json'));local=json.loads(read(doc+'localization-results.json'));origin=json.loads(original.extractfile(source['source-inputs.json']).read())
    for rel,r in origin['files'].items():assert sha(original.extractfile(source[rel]).read())==r['sha256'],rel
    for rel,h in manifest.items():assert sha(read('clang64/'+rel))==h,rel
    payload={n for n in members if n.startswith('clang64/')};assert payload=={'clang64/'+rel for rel in manifest}|{doc+'payload-sha256.json'}
    assert len(build['original_source_sha256'])==15 and build['original_framework']=='netstandard2.0' and build['original_production_source_changes']==0
    for rel,h in build['original_source_sha256'].items():assert sha(original.extractfile(source[rel]).read())==h,rel
    assert len(refs['projects'])==9
    for r in refs['projects']:
        assert r['original_framework']=='netstandard2.0' and r['reference_only']
        for rel,h in r['original_source_sha256'].items():assert sha(original.extractfile(source[rel]).read())==h,rel
        path='clang64/lib/dotnet/reference-packs/sdk10-releases-vmr-44525024/'+r['assembly']+'/'+r['package_version']+'/netstandard2.0/'+r['assembly']+'.dll'
        assert sha(read(path))==r['output_sha256']
    assert len(local['satellite_sha256'])==13
    for rel,h in local['original_xlf_sha256'].items():assert sha(original.extractfile(source['src/deployment-tools/'+rel]).read())==h,rel
    path='clang64/lib/dotnet/library-packs/'+name.lower()+'.'+version+'.nupkg'
    with zipfile.ZipFile(io.BytesIO(read(path))) as z:
        meta=E.fromstring(z.read(name+'.nuspec'));assert meta.findtext('./metadata/id')==name and meta.findtext('./metadata/version')==version
        group=meta.find('./metadata/dependencies/group');assert group.get('targetFramework')=='netstandard2.0' and {e.get('id'):e.get('version') for e in group}=={'System.Text.Json':'[8.0.5]'}
        for ext,h in build['output_sha256'].items():assert sha(z.read('lib/netstandard2.0/'+name+'.'+ext))==h
        for rel,h in local['satellite_sha256'].items():assert sha(z.read('lib/netstandard2.0/'+rel))==h
        assert not any(n.endswith('System.Text.Json.dll') or '/reference-packs/' in n for n in z.namelist()),'References must not enter the runtime archive'
    nupkg_hash=sha(read(path));info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-deployment-releases-bootstrap\n' in info and 'pkgver = 2.0.0.preview1.25612.105-1\n' in info
report=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(payload),source_snapshot_sha256=sha(snapshot.read_bytes()),original_vmr_source_files=len(origin['files']),original_production_cs=15,original_framework='netstandard2.0',original_reference_only_assets=9,reference_assets_separate_from_runtime_archive=True,localized_satellites=13,source_nuget_archive_sha256=nupkg_hash,all_original_source_and_payload_bytes_verified=True,full_json8_standard_runtime_implementation_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS actual Releases NS2 archive,15 original sources,13 satellites and9 separate reference-only assets')
