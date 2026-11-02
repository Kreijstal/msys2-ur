"""Inspect the actual package archive independently against its original source archive."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
package,source,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source.read_bytes())=='3dc1eeeb8f781122e0713481bad993329c669feb9928cc4ec86e0ab24d9eff9e'
doc='clang64/share/doc/dotnet-newtonsoft-json1303-bootstrap/'
with tarfile.open(package) as t:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()}
    def read(n):return t.extractfile(members[n]).read()
    manifest=json.loads(read(doc+'payload-sha256.json'))
    for n,h in manifest.items():assert sha(read('clang64/'+n))==h,n
    payload={n for n in members if n.startswith('clang64/')};assert payload=={'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
    build=json.loads(read(doc+'build-results.json'));checks=json.loads(read(doc+'build-check-results.json'))
    assert len(build['original_source_sha256'])==checks['original_sources_verified']==233
    assert build['original_project_supported_framework']=='netstandard2.0' and build['original_production_source_changes']==0
    assert build['original_build_file_version_policy_verified'] and len(build['actual_reference_sha256'])==113
    with tarfile.open(source) as s:
        inputs={m.name.partition('/')[2]:m for m in s.getmembers() if m.isfile()}
        for rel,h in build['original_source_sha256'].items():assert sha(s.extractfile(inputs[rel]).read())==h,rel
        assert sha(s.extractfile(inputs['Src/Newtonsoft.Json.Tests/JsonConvertTest.cs']).read())==checks['upstream_test_source_sha256']
    path='clang64/lib/dotnet/library-packs/newtonsoft.json.13.0.3.nupkg'
    with zipfile.ZipFile(io.BytesIO(read(path))) as z:
        assert sha(z.read('lib/netstandard2.0/Newtonsoft.Json.dll'))==build['output_sha256']
        meta=E.fromstring(z.read('Newtonsoft.Json.nuspec'));assert meta.findtext('./metadata/id')=='Newtonsoft.Json' and meta.findtext('./metadata/version')=='13.0.3'
        assert meta.find('./metadata/dependencies/group').get('targetFramework')=='netstandard2.0'
    nupkg_sha256=sha(read(path))
    info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-newtonsoft-json1303-bootstrap\n' in info and 'pkgver = 13.0.3-1\n' in info
report=dict(package=package.name,package_sha256=sha(package.read_bytes()),source_archive_sha256=sha(source.read_bytes()),regular_payload_files=len(payload),all_payload_bytes_and_inventory_verified=True,original_source_files_verified=233,reference_assets=113,original_framework='netstandard2.0',source_nuget_archive_sha256=nupkg_sha256,other_original_framework_profiles_built=False,full_upstream_test_suite_run=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS actual Newtonsoft13.0.3 package inventory,original233 source hashes and NETStandard2 archive')
