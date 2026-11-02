"""Independently verify the eight-library archive against original source and metadata."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,xml.etree.ElementTree as E,zipfile
package,source,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source.read_bytes())=='9eb1139d9abecfab7d69fd7b02cb58d20792a0cd46ffb7b2ea6a12bbfda48f12'
doc='clang64/share/doc/dotnet-nuget73-libraries-bootstrap/';runtime='clang64/lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin/'
version='7.3.0-preview.1.11413';names=['NuGet.Configuration','NuGet.Packaging','NuGet.Protocol','NuGet.DependencyResolver.Core','NuGet.ProjectModel','NuGet.Credentials','NuGet.Resolver','NuGet.Commands']
with tarfile.open(package) as t,tarfile.open(source) as upstream:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()};original={m.name.partition('/')[2]:m for m in upstream.getmembers() if m.isfile()}
    def read(n):return t.extractfile(members[n]).read()
    manifest=json.loads(read(doc+'payload-sha256.json'))
    for rel,h in manifest.items():assert sha(read('clang64/'+rel))==h,rel
    payload={n for n in members if n.startswith('clang64/')};assert payload=={'clang64/'+rel for rel in manifest}|{doc+'payload-sha256.json'}
    build=json.loads(read(doc+'build-results.json'));local=json.loads(read(doc+'localization-results.json'));audit=json.loads(read(doc+'source-audit.json'))
    assert [r['assembly'] for r in build['projects']]==names and audit['original_compile_items']==1081 and len(local['satellite_sha256'])==104
    central=E.fromstring(upstream.extractfile(original['Directory.Packages.props']).read());properties={p.tag:p.text for g in central.findall('PropertyGroup') for p in g};versions={p.get('Include'):p.get('Version') for g in central.findall('ItemGroup') for p in g if p.tag=='PackageVersion'}
    archives=[];source_count=0;original_projects={}
    for r in build['projects']:
        name=r['assembly'];assert r['original_target']=='net10.0' and r['original_production_source_changes']==0
        for kind in ['original_source_sha256','original_resource_sha256']:
            for rel,h in r[kind].items():assert sha(upstream.extractfile(original[rel]).read())==h,rel
        source_count+=len(r['original_source_sha256']);assert sha(read(runtime+name+'.dll'))==r['output_sha256'];assert sha(read(runtime+name+'.xml'))==r['xml_documentation_sha256']
        xml=E.fromstring(read(runtime+name+'.xml'));assert xml.findtext('assembly/name')==name and xml.find('members') is not None
        rel='src/NuGet.Core/'+name+'/'+name+'.csproj';original_project=upstream.extractfile(original[rel]).read();original_projects[rel]=sha(original_project);tree=E.fromstring(original_project)
        deps={Path(p.get('Include').replace('\\','/')).stem:'['+version+']' for p in tree.iter('ProjectReference')}
        for p in r['declared_package_references']:
            dep=p['identity'];v=versions[dep]
            if v.startswith('$('):v=properties[v[2:-1]]
            deps[dep]='['+v+']'
        path='clang64/lib/dotnet/library-packs/'+name.lower()+'.'+version+'.nupkg'
        with zipfile.ZipFile(io.BytesIO(read(path))) as z:
            meta=E.fromstring(z.read(name+'.nuspec'));assert meta.findtext('./metadata/id')==name and meta.findtext('./metadata/version')==version
            group=meta.find('./metadata/dependencies/group');assert group.get('targetFramework')=='net10.0'
            assert {p.get('id'):p.get('version') for p in group}==deps,(name,deps)
            for ext in ['dll','pdb','xml']:assert z.read('lib/net10.0/'+name+'.'+ext)==read(runtime+name+'.'+ext)
            assert not any(n.endswith('.resources.dll') for n in z.namelist())
        archives.append(dict(id=name,version=version,sha256=sha(read(path)),dependencies=deps))
    assert source_count==1081
    for rel,h in local['original_xlf_sha256'].items():assert sha(upstream.extractfile(original[rel]).read())==h,rel
    for rel,h in local['satellite_sha256'].items():assert sha(read(runtime+rel))==h,rel
    info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-nuget73-libraries-bootstrap\n' in info and 'pkgver = 7.3.0.preview1.11413-1\n' in info
report=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(payload),original_compile_items=source_count,original_project_sha256=original_projects,localized_satellites=104,original_xml_documentation_verified=True,all_payload_bytes_and_inventory_verified=True,exact_original_dependency_metadata_verified=True,source_nuget_archives=archives,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('PASS actual eight-library NuGet7.3 package,original1081 sources,XML documentation,104 satellites and exact dependency metadata')
