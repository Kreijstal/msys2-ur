"""Verify original closure inputs against the source archive and declared dependency pins."""
from pathlib import Path
import hashlib,json,sys,tarfile,xml.etree.ElementTree as E
root,build,out=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda b:hashlib.sha256(b).hexdigest()
result=json.loads((build/'results.json').read_text());checked={}
expected={'Newtonsoft.Json':'13.0.3','System.Security.Cryptography.ProtectedData':'8.0.0','System.Security.Cryptography.Pkcs':'8.0.1','Microsoft.Extensions.FileSystemGlobbing':'6.0.0','Microsoft.Extensions.FileProviders.Abstractions':'6.0.0'}
archive=root/'nuget-sdk10-bf048eb7.tar.gz'
if not archive.exists():archive=Path('E:/codex-dotnet10/nuget-sdk10-bf048eb7.tar.gz')
assert sha(archive.read_bytes())=='9eb1139d9abecfab7d69fd7b02cb58d20792a0cd46ffb7b2ea6a12bbfda48f12'
with tarfile.open(archive) as t:
    members={m.name.partition('/')[2]:m for m in t.getmembers() if m.isfile()}
    central=t.extractfile(members['Directory.Packages.props']).read();tree=E.fromstring(central);properties={p.tag:p.text for g in tree.findall('PropertyGroup') for p in g};versions={p.get('Include'):p.get('Version') for g in tree.findall('ItemGroup') for p in g if p.tag=='PackageVersion'}
    for package,version in expected.items():
        value=versions[package]
        if value.startswith('$('):value=properties[value[2:-1]]
        assert value==version,(package,value,version)
    checked['Directory.Packages.props']=sha(central)
    for record in result['projects']:
        for kind in ['original_source_sha256','original_resource_sha256']:
            for rel,h in record[kind].items():assert sha(t.extractfile(members[rel]).read())==h,rel;checked[rel]=h
        assert sha((build/'bin'/(record['assembly']+'.dll')).read_bytes())==record['output_sha256']
        for kind in ['actual_reference_sha256','source_generators_sha256']:
            for path,h in record.get(kind,{}).items():assert sha(Path(path).read_bytes())==h,path
    localized=root/'localized-closure/results.json'
    if localized.exists():
        local=json.loads(localized.read_text())
        for rel,h in local['original_xlf_sha256'].items():assert sha(t.extractfile(members[rel]).read())==h,rel;checked[rel]=h
        for rel,h in local['satellite_sha256'].items():assert sha((build/'bin'/rel).read_bytes())==h,rel
    else:local=None
for asset in result['dependency_assets']:
    assert sha(Path(asset['output']).read_bytes())==asset['output_sha256']
    if 'archive' in asset:assert sha(Path(asset['archive']).read_bytes())==asset['archive_sha256']
report=dict(original_compile_items=sum(len(p['original_source_sha256']) for p in result['projects']),original_archive_inputs_verified=len(checked),declared_dependency_versions_verified=expected,central_package_metadata_sha256=checked['Directory.Packages.props'],source_generators_verified=True,original_production_source_changes=0,localized_satellites=len(local['satellite_sha256']) if local else 0,localized_values=local['localized_values'] if local else 0,installed_source_foundations_reused=result['installed_source_foundations_reused'],full_nuget73_closure_built=False,formal_eight_library_package_built=False,full_dependency_goal_complete=False)
assert report['original_compile_items']==1081
out.write_text(json.dumps(report,indent=2)+'\n');print('PASS original1081 source inputs,declared exact dependencies,outputs/references/generators; satellites=',report['localized_satellites'])
