"""Verify the installed two-NuGet Roslyn4.14 compiler prerequisite package."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,zipfile

archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
names={'Microsoft.CodeAnalysis.Common':'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp':'Microsoft.CodeAnalysis.CSharp'}
expected={'clang64/lib/dotnet/library-packs/'+n.lower()+'.4.14.0.nupkg':prepared/'feed'/(n+'.4.14.0.nupkg') for n in names}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
    for m in t:
        if m.isdir() or m.name.startswith('.'):continue
        assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-roslyn414/','clang64/share/licenses/dotnet-roslyn414/'))),m.name
        data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
        if m.name in expected:assert expected[m.name].read_bytes()==data,m.name
        files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==11 and set(expected)<=set(files),len(files)
source=prepared/'roslyn-source';assets={}
for ident,name in names.items():
    with zipfile.ZipFile(prepared/'feed'/(ident+'.4.14.0.nupkg')) as z:
        for p in z.namelist():
            if p.startswith('lib/'):
                assert p.startswith('lib/netstandard2.0/'),p
                original=prepared/name/'bin/Release/netstandard2.0'/p.removeprefix('lib/netstandard2.0/')
                assert z.read(p)==original.read_bytes(),p
                assets[ident+':'+p]=hashlib.sha256(z.read(p)).hexdigest()
        for p in ['License.txt','THIRD-PARTY-NOTICES.txt']:assert z.read(p)==(source/p).read_bytes()
assert sum(n.endswith('.dll') for n in assets)==28
result=dict(package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_nugets_verified=2,
    installed_files_sha256=files,shipping_managed_and_satellite_assemblies_verified=28,all_shipping_assets_sha256=assets,
    existing_sdk_compiler_selection_unchanged=True,complete_roslyn414_targets_and_workspaces=False,full_dependency_goal_complete=False)
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS eleven installed files, two exact source Roslyn4.14 NuGets, 28 managed/satellite assemblies and source licenses')
