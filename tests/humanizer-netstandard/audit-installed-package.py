"""Verify every installed Humanizer package byte and the two source framework assets."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile

archive,prepared,output=(Path(p).resolve() for p in sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed=['clang64/lib/dotnet/library-packs/humanizer.core.2.14.1.nupkg',
         'clang64/share/licenses/dotnet-humanizer/', 'clang64/share/doc/dotnet-humanizer/']
files={};process=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout,mode='r|') as t:
    for m in t:
        if m.isdir() or m.name.startswith('.'):continue
        assert m.isfile() and (m.name==allowed[0] or any(m.name.startswith(p) for p in allowed[1:])),m.name
        data=t.extractfile(m).read();assert (Path('/')/m.name).read_bytes()==data,m.name
        files[m.name]=hashlib.sha256(data).hexdigest()
assert process.wait()==0
assert len(files)==8,len(files)
package=Path('/')/allowed[0]
assert package.read_bytes()==(prepared/'feed/Humanizer.Core.2.14.1.nupkg').read_bytes()
record=json.loads((prepared/'source-inputs.json').read_text());source=prepared/('Humanizer-'+record['source_commit'])
assets={}
with zipfile.ZipFile(package) as z:
    for name in z.namelist():
        if not name.startswith('lib/'):continue
        parts=name.split('/');assert parts[1] in ['netstandard2.0','net8.0']
        original=source/'src/Humanizer/bin/Release'/parts[1]/'/'.join(parts[2:])
        assert z.read(name)==original.read_bytes(),name
        assets[name]=hashlib.sha256(z.read(name)).hexdigest()
    for relative,name in [('LICENSE','LICENSE'),('src/Humanizer/Bytes/LICENSE','LICENSE.Bytes'),('src/Humanizer/Inflections/LICENSE','LICENSE.Inflections')]:assert z.read(name)==(source/relative).read_bytes()
assert sum(n.endswith('.dll') for n in assets)==100
result=dict(package_archive_sha256=sha(archive),installed_payload_files_verified=len(files),installed_files_sha256=files,
    installed_nuget_sha256=sha(package),original_standard20_and_retained_net8_assets_verified=assets,shipping_managed_assemblies=100,
    three_original_licenses_verified=True,all_original_target_variants_complete=False,full_dependency_goal_complete=False)
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS eight installed payload files, exact two-target Humanizer NuGet, 100 source DLLs and three original licenses')
