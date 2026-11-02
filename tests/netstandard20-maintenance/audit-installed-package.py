"""Check the installed maintenance bundle and exact source-built NuGet payloads."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
manifest=json.loads((prepared/'source-inputs.json').read_text())
expected={('clang64/lib/dotnet/library-packs/'+n+'.'+r['version']+'.nupkg').lower():prepared/'feed'/(n+'.'+r['version']+'.nupkg') for n,r in manifest['projects'].items()}
names=subprocess.check_output(['bsdtar','-tf',str(archive)],text=True).splitlines();assert len(names)==len(set(names))
files={}
for name in names:
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    if name.endswith('/'):continue
    if name.startswith('.'):
        assert name in {'.PKGINFO','.BUILDINFO','.MTREE'},name
        continue
    assert name in expected or name.startswith(('clang64/share/doc/dotnet-maintenance-netstandard/','clang64/share/licenses/dotnet-maintenance-netstandard/')),name
    data=subprocess.check_output(['bsdtar','-xOf',str(archive),name])
    assert (Path('/')/name).read_bytes()==data,name
    if name in expected:assert expected[name].read_bytes()==data,name
    files[name]=hashlib.sha256(data).hexdigest()
assert len(files)==15 and set(expected)<=set(files)
assert not any(n.endswith('.dll') for n in files)
report=dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),installed_payload_files_verified=len(files),installed_nugets_verified=5,installed_files_sha256=files,all_installed_nuget_bytes_match_source_build=True,no_framework_or_global_implementation_dlls_installed=True,dedicated_paths_verified=True,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print('PASS all 15 installed bundle files, five exact source NuGets and dedicated feed/doc/license paths')
