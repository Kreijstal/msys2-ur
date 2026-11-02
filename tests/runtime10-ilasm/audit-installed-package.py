"""Verify the exact installed native assembler payload and native imports."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess
import sys

archive, prepared, output = (Path(p).resolve() for p in sys.argv[1:])
names = subprocess.check_output(['bsdtar','-tf',str(archive)],text=True).splitlines()
assert len(names)==len(set(names))
records={}
for name in names:
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    if name.endswith('/'):continue
    if name.startswith('.'):
        assert name in {'.PKGINFO','.BUILDINFO','.MTREE'},name
        continue
    assert name=='clang64/bin/ilasm10.exe' or name.startswith(('clang64/share/doc/dotnet-ilasm10/','clang64/share/licenses/dotnet-ilasm10/')),name
    data=subprocess.check_output(['bsdtar','-xOf',str(archive),name])
    assert (Path('/')/name).read_bytes()==data,name
    records[name]=hashlib.sha256(data).hexdigest()
assert len(records)==10
image=Path('/clang64/bin/ilasm10.exe')
assert image.read_bytes()==(prepared/'coreclr-build/ilasm/ilasm.exe').read_bytes()
imports=subprocess.check_output(['/clang64/bin/llvm-readobj.exe','--coff-imports',str(image)],text=True)
names=re.findall(r'^\s+Name: (.+)$',imports,re.M)
assert names
assert not {n.lower() for n in names}&{'coreclr.dll','clr.dll','mscoree.dll','hostfxr.dll','mono-2.0-sgen.dll'}
report=dict(package_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),installed_files_verified=len(records),
            installed_files_sha256=records,installed_image_matches_source_build=True,native_imports=names,
            native_executable_has_no_clr_runtime_imports=True,dedicated_paths_verified=True,full_dependency_goal_complete=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print('PASS exact installed assembler archive/source bytes, dedicated paths and native imports')
