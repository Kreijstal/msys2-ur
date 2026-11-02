"""Independently inspect the actual NET10 NuGet foundation pacman archive."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile

package,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest();doc='clang64/share/doc/dotnet-nuget73-core-bootstrap/';runtime='clang64/lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin/'
with tarfile.open(package) as t:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()}
    def read(n):return t.extractfile(members[n]).read()
    def load(n):return json.loads(read(doc+n))
    manifest=load('payload-sha256.json')
    for n,h in manifest.items():assert sha(read('clang64/'+n))==h,n
    payload={n for n in members if n.startswith('clang64/')};assert payload=={'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
    build=load('build-results.json');localization=load('localization-results.json');audit=load('source-audit.json')
    assert audit['original_compile_items']==187 and audit['original_xlf_inputs']==52
    packages=[]
    for r in build['projects']:
        name=r['assembly'];assert sha(read(runtime+name+'.dll'))==r['output_sha256'];assert r['original_target']=='net10.0' and r['original_production_source_changes']==0
        path='clang64/lib/dotnet/library-packs/'+name.lower()+'.7.3.0-preview.1.11413.nupkg'
        with zipfile.ZipFile(io.BytesIO(read(path))) as z:
            meta=E.fromstring(z.read(name+'.nuspec'));assert meta.findtext('./metadata/id')==name and meta.findtext('./metadata/version')=='7.3.0-preview.1.11413'
            for ext in ['dll','pdb','xml']:assert z.read('lib/net10.0/'+name+'.'+ext)==read(runtime+name+'.'+ext)
            assert not any(n.endswith('.resources.dll') for n in z.namelist()),'Upstream excludes library satellites from individual packages'
        packages.append(dict(id=name,version='7.3.0-preview.1.11413',sha256=sha(read(path))))
    assert len(localization['satellite_sha256'])==52
    for n,h in localization['satellite_sha256'].items():assert sha(read(runtime+n))==h,n
    info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-nuget73-core-bootstrap\n' in info and 'pkgver = 7.3.0.preview1.11413-1\n' in info
    report=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(payload),all_payload_bytes_and_inventory_verified=True,four_source_nuget_assets_byte_match_loose_outputs=True,upstream_individual_package_satellite_exclusion_preserved=True,localized_satellites=52,source_nuget_packages=packages,source_audit=audit,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS actual NuGet7.3 foundation package',report['regular_payload_files'],'payload files,four source NuGet archives and52 original satellites')
