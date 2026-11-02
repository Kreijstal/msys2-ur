"""Verify the installed twelve-package source runtime9 component."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
manifest=json.loads((prepared/'source-inputs.json').read_text())
names=manifest['order']+['System.Composition']
expected={('clang64/lib/dotnet/library-packs/'+n+'.9.0.0.nupkg').lower():prepared/'feed'/(n+'.9.0.0.nupkg') for n in names}
entries=subprocess.check_output(['bsdtar','-tf',str(archive)],text=True).splitlines();assert len(entries)==len(set(entries))
files={}
for name in entries:
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    if name.endswith('/'):continue
    if name.startswith('.'):
        assert name in {'.PKGINFO','.BUILDINFO','.MTREE'},name
        continue
    assert name in expected or name.startswith(('clang64/share/doc/dotnet-runtime9-libraries/','clang64/share/licenses/dotnet-runtime9-libraries/')),name
    data=subprocess.check_output(['bsdtar','-xOf',str(archive),name]);assert (Path('/')/name).read_bytes()==data,name
    if name in expected:assert expected[name].read_bytes()==data,name
    files[name]=hashlib.sha256(data).hexdigest()
assert len(files)==21 and set(expected)<=set(files)
assert not any(p.endswith('.dll') for p in files)
report=dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),installed_payload_files_verified=len(files),installed_nugets_verified=12,installed_files_sha256=files,all_installed_nugets_match_source_build=True,no_global_or_framework_implementation_dlls_installed=True,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print('PASS 21 installed payload files and twelve exact source NuGets in dedicated feed/doc/license paths')
