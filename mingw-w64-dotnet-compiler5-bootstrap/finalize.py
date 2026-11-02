"""Declare the freshly built runtime9 assets in the compiler host dependency graph."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

out = Path(sys.argv[1]).resolve()
compiler = out / 'compiler'
deps = json.loads((compiler / 'CompilerHost.deps.json').read_text())
target = deps['targets'][deps['runtimeTarget']['name']]
app = target['CompilerHost/1.0.0']
app.setdefault('dependencies', {})
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assets = {}
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']:
    source = out / name / 'bin/Release/net8.0' / (name + '.dll')
    shutil.copyfile(source, compiler / source.name)
    app['dependencies'][name] = '9.0.0'
    target[name + '/9.0.0'] = dict(runtime={name + '.dll': dict(assemblyVersion='9.0.0.0', fileVersion='9.0.0.0')})
    deps['libraries'][name + '/9.0.0'] = dict(type='project', serviceable=False, sha512='')
    assets[name] = sha(source)
(compiler / 'CompilerHost.deps.json').write_text(json.dumps(deps, indent=2) + '\n')
original = Path('/clang64/lib/dotnet-bootstrap/roslyn-5.0.0')
for name in ['csc.exe', 'Microsoft.CodeAnalysis.dll', 'Microsoft.CodeAnalysis.CSharp.dll']:
    assert (compiler / name).read_bytes() == (original / name).read_bytes()
(out / 'host-assets.json').write_text(json.dumps(dict(runtime9_assets_sha256=assets, original_compiler_files_unchanged=True), indent=2) + '\n')
print('PASS explicit source runtime9 host dependencies and unchanged compiler libraries')
