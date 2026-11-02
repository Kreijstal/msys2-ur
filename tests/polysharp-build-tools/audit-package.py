"""Verify final MSBuild data archives against both pinned original repositories."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

artifact, archives, output = map(Path, sys.argv[1:])
sha = lambda data: hashlib.sha256(data).hexdigest()
with tarfile.open(artifact) as t:
    files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
doc='clang64/share/doc/dotnet-polysharp-build-tools/'
contracts=json.loads(files[doc+'contracts.json'])
source=json.loads(files[doc+'source-results.json'])
check=json.loads(files[doc+'producer-check-results.json'])
assert check['upstream_CI_vectors_executed']==22 and check['upstream_branch_vectors_executed']==90
assert check['actual_embedded_PDB'] and check['NoTargets_data_pack_and_clean']
assert check['original_build_MultiTargeting_and_Transitive_imports'] and check['exact_cached_archive_and_original_content_bytes']
assert all(c['exit_code']==c['expected_exit_code'] for c in check['commands'])
assert [c['exit_code'] for c in check['commands']].count(1)==1
packages={}
for ident,contract in contracts.items():
    archive=archives/Path(contract['source_archive']).name
    assert sha(archive.read_bytes())==contract['source_archive_sha256']
    commit=contract.get('source_commit') or contract['repository']['commit']
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment']==commit
        originals={m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile()}
    data=files['clang64/lib/dotnet/library-packs/'+ident.lower()+'.'+contract['version']+'.nupkg']
    record=source['packages'][ident]
    assert record['source_changes']==0 and record['source_commit']==commit
    assert sha(originals[record['original_project']])==record['original_project_sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        md=E.fromstring(z.read(ident+'.nuspec')).find('{*}metadata')
        assert md.findtext('{*}id')==ident and md.findtext('{*}version')==contract['version']
        assert md.find('{*}repository').get('commit')==commit
        for member,expected in contract['original_build_file_contract'].items():
            assert z.read(member)==originals[expected['source_path']]
            assert sha(z.read(member))==expected['source_sha256']
        for member,digest in record['content_sha256'].items():assert sha(z.read(member))==digest
        assert not any(n.lower().endswith(('.dll','.exe','.pdb')) for n in z.namelist())
        if ident=='Microsoft.Build.NoTargets':
            assert md.find('{*}packageTypes/{*}packageType').get('name')=='MSBuildSdk'
            assert md.find('{*}dependencies/{*}group').get('targetFramework')=='.NETFramework4.7.2'
            assert record['original_project_framework']=='net472'
            assert z.read('LICENSE.txt')==originals['LICENSE.txt']
            assert z.read('MSBuild-NuGet-Icon.png')==originals['branding/MSBuild-NuGet-Icon.png']
        else:
            assert record['original_project_framework']=='netstandard1.0'
            assert md.findtext('{*}developmentDependency')=='true'
            assert z.read('README.md')==originals['README.md']
    license='LICENSE.txt' if ident=='Microsoft.Build.NoTargets' else 'LICENSE'
    assert files['clang64/share/licenses/dotnet-polysharp-build-tools/'+ident+'/LICENSE']==originals[license]
    packages[ident]=dict(version=contract['version'],source_commit=commit,nupkg_sha256=sha(data),original_build_files=len(contract['original_build_file_contract']))
for name in ['check.py','contracts.json','README.md']:
    assert files[doc+name]==(Path('mingw-w64-dotnet-polysharp-build-tools')/name).read_bytes()
report=dict(artifact=artifact.name,artifact_sha256=sha(artifact.read_bytes()),packages=packages,
    original_build_file_changes=0,contains_implementation_binaries=False,
    upstream_CI_vectors_executed=22,upstream_branch_vectors_executed=90,
    original_MSBuild_version_guard_cases=3,original_release_toolchain_replayed=False,
    payload_sha256={n:sha(b) for n,b in files.items() if n.startswith('clang64/')},
    full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
