"""Require the original empty-input failure after a successful direct native call."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

build, runtime_check, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
native = lambda p: Path(p).resolve().as_posix()
record = json.loads((build / 'results.json').read_text())
source = Path(record['source_root'])
original = source / 'src/System.Security.Cryptography.ProtectedData/src/System/Security/Cryptography/ProtectedData.cs'
overlay = Path(record['production_overlay']['path'])
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
name = 'System.Security.Cryptography.ProtectedData'
destination = out / (name + '.dll')
rsp = (build / 'compile.rsp').read_text()
assert rsp.count('"' + native(overlay) + '"') == 1
rsp = rsp.replace('"' + native(overlay) + '"', '"' + native(original) + '"')
lines = rsp.splitlines()
outputs = [i for i, line in enumerate(lines) if line.startswith('/out:')]
assert len(outputs) == 1
assert lines[outputs[0]].endswith('/' + destination.name + '"')
lines[outputs[0]] = '/out:"' + native(destination) + '"'
rsp = '\n'.join(lines) + '\n'
assert rsp.count('/out:') == 1 and '/out:"' + native(destination) + '"' in rsp
(out / 'compile.rsp').write_text(rsp)
commands = []
for label, host, cmd in [
    ('compile', host10, [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')]),
    ('execute', host8, [host8, runtime_check / 'Check.dll', destination, runtime_check / 'expected-resources.json'])]:
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    if label == 'compile':
        assert r.returncode == 0
    else:
        assert r.returncode != 0
        text = (out / 'execute.log').read_text(encoding='utf-8')
        assert 'PASS independent native DPAPI input-bytes=0' in text and 'WindowsCryptographicException' in text
        assert 'DPAPI scope=LocalMachine' not in text
(out / 'results.json').write_text(json.dumps(dict(commands=commands,
    original_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
    original_source_empty_input_failure_reproduced_after_native_success=True,
    expected_negative_case_exit_code=commands[-1]['exit_code'], full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS original-source negative case: native empty DPAPI succeeds, original managed pointer fails; repaired full fixture passes separately')
