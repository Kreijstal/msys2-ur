"""Give the unchanged source Compiler5 adapter explicit source Immutable/Metadata9."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

root, out = (Path(p).resolve() for p in sys.argv[1:])
original = root / 'cdac-bootstrap5/compiler'
assert not out.exists(), out
shutil.copytree(original, out)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    return base + '/' + p.resolve().relative_to(root).as_posix()
deps = json.loads((out / 'CompilerHost.deps.json').read_text())
target = deps['targets'][deps['runtimeTarget']['name']]
app = target['CompilerHost/1.0.0']
app.setdefault('dependencies', {})
records = {}
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']:
    package = root / 'roslyn-deps9-1/feed' / (name + '.9.0.0.nupkg')
    with zipfile.ZipFile(package) as archive:
        path = 'lib/net8.0/' + name + '.dll'
        (out / (name + '.dll')).write_bytes(archive.read(path))
    ident = name + '/9.0.0'
    app['dependencies'][name] = '9.0.0'
    target[ident] = {'runtime': {name + '.dll': {'assemblyVersion': '9.0.0.0', 'fileVersion': '9.0.0.0'}}}
    deps['libraries'][ident] = {'type': 'project', 'serviceable': False, 'sha512': ''}
    records[name] = dict(source_package_sha256=sha(package), source_asset=path, dll_sha256=sha(out / (name + '.dll')))
(out / 'CompilerHost.deps.json').write_text(json.dumps(deps, indent=2) + '\n')
(out / 'csc50.cmd').write_text('@echo off\r\n"E:/msys64/clang64/lib/dotnet/dotnet.exe" "' + native(out / 'CompilerHost.dll') + '" %*\r\nexit /b %errorlevel%\r\n')
for name in ['CompilerHost.dll', 'Microsoft.CodeAnalysis.dll', 'Microsoft.CodeAnalysis.CSharp.dll', 'csc.exe']:
    assert (out / name).read_bytes() == (original / name).read_bytes()
(out / 'host-source-inputs.json').write_text(json.dumps(dict(unchanged_compiler_sha256={name: sha(out / name) for name in ['CompilerHost.dll', 'Microsoft.CodeAnalysis.dll', 'Microsoft.CodeAnalysis.CSharp.dll', 'csc.exe']}, explicit_source_runtime_dependencies=records, framework='net8.0', original_host_unchanged=True, full_dependency_goal_complete=False), indent=2) + '\n')
print('Prepared source Compiler5 host with explicit source runtime9 dependencies')
