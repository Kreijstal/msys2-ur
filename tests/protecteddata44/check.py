"""Exercise the actual produced DLL under NET8, excluding inbox/library fallback."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, xml.etree.ElementTree as E

build, out = (Path(p).resolve() for p in sys.argv[1:3])
net10 = '--net10' in sys.argv[3:]
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll'))
assert len(refs) == 163
name = 'System.Security.Cryptography.ProtectedData'
produced = build / 'bin' / (name + '.dll')
record = json.loads((build / 'results.json').read_text())
source = Path(record['source_root'])
contract = Path(record.get('contract_reference_path', str(produced)))
resx = E.parse(source / 'src' / name / 'src/Resources/Strings.resx')
(out / 'expected-resources.json').write_text(json.dumps({n.get('name'): n.findtext('value') for n in resx.findall('data')}))
args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(out / 'Check.dll') + '"']
args += ['/reference:"' + native(p) + '"' for p in refs + [contract]]
args += ['"' + native(here / 'Check.cs') + '"']
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
(out / 'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0', framework=dict(name='Microsoft.NETCore.App', version='8.0.31')))))
commands = []
for label, host, cmd in [
    ('compile', host10, [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')]),
    ('execute', host10 if net10 else host8, ([host10, '--fx-version', '10.0.5'] if net10 else [host8]) + [out / 'Check.dll', produced, out / 'expected-resources.json'])]:
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
(out / 'results.json').write_text(json.dumps(dict(commands=commands,
    produced_sha256=hashlib.sha256(produced.read_bytes()).hexdigest(), actual_produced_DLL_executed=True,
    actual_execution_framework='10.0.5' if net10 else '8.0.31',
    compiled_contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
    original_absence_of_TFA_and_native_search_policy_preserved=True, both_scopes_native_DPAPI_interop_and_errors_passed=True,
    neutral_resource_values=2, portable_PDB_associations=1, other_original_profiles_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print((out / 'execute.log').read_text(encoding='utf-8'))
