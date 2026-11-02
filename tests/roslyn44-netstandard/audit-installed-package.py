"""Verify the installed four-NuGet Roslyn4.4 compiler/Workspaces prerequisite package."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,zipfile

archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
names={'Microsoft.CodeAnalysis.Common':'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp':'Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces.Common':'Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces':'Microsoft.CodeAnalysis.CSharp.Workspaces'}
expected={'clang64/lib/dotnet/library-packs/'+n.lower()+'.4.4.0.nupkg':prepared/'feed'/(n+'.4.4.0.nupkg') for n in names}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
    for m in t:
        if m.isdir() or m.name.startswith('.'):continue
        assert m.isfile() and (m.name in expected or m.name.startswith(('clang64/share/doc/dotnet-roslyn44/','clang64/share/licenses/dotnet-roslyn44/'))),m.name
        data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
        if m.name in expected:assert expected[m.name].read_bytes()==data,m.name
        files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==14 and set(expected)<=set(files),len(files)
source=prepared/'roslyn-source';assets={}
for ident,name in names.items():
    with zipfile.ZipFile(prepared/'feed'/(ident+'.4.4.0.nupkg')) as z:
        for p in z.namelist():
            if p.startswith('lib/'):
                assert p.startswith('lib/netstandard2.0/'),p
                original=prepared/name/'bin/Release/netstandard2.0'/p.removeprefix('lib/netstandard2.0/')
                assert z.read(p)==original.read_bytes(),p
                assets[ident+':'+p]=hashlib.sha256(z.read(p)).hexdigest()
        for p in ['License.txt','THIRD-PARTY-NOTICES.txt']:assert z.read(p)==(source/p).read_bytes()
assert sum(n.endswith('.dll') for n in assets)==56
result=dict(package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_nugets_verified=4,
    installed_files_sha256=files,shipping_managed_and_satellite_assemblies_verified=56,all_shipping_assets_sha256=assets,
    existing_sdk_compiler_selection_unchanged=True,complete_roslyn44_original_target_variants=False,full_dependency_goal_complete=False)
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS fourteen installed files, four exact source Roslyn4.4 NuGets, 56 managed/satellite assemblies and source licenses')
