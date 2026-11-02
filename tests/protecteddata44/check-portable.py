"""Verify the actual portable DLL throws the original source resource message."""
from pathlib import Path
import json, os, subprocess, sys, xml.etree.ElementTree as E

build, out = (Path(p).resolve() for p in sys.argv[1:])
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
source = Path(json.loads((build / 'results.json').read_text())['source_root'])
resx = E.parse(source / 'src' / name / 'src/Resources/Strings.resx')
message = next(n.findtext('value') for n in resx.findall('data') if n.get('name') == 'PlatformNotSupported_CryptographyProtectedData')
(out / 'expected-resources.json').write_text(json.dumps({n.get('name'): n.findtext('value') for n in resx.findall('data')}))
produced = build / 'bin' / (name + '.dll')
record = json.loads((build / 'results.json').read_text())
contract = Path(record.get('contract_reference_path', str(produced)))
args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(out / 'Check.dll') + '"']
args += ['/reference:"' + native(p) + '"' for p in refs + [contract]] + ['"' + native(here / 'CheckPortable.cs') + '"']
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
(out / 'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0', framework=dict(name='Microsoft.NETCore.App', version='8.0.31')))))
commands = []
for label, host, cmd in [
    ('compile', host10, [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')]),
    ('execute', host8, [host8, out / 'Check.dll', produced, message, out / 'expected-resources.json'])]:
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, original_portable_API_PNSE_and_resource_message_passed=True,
    original_portable_identity_and_absence_of_TFA_verified=True, actual_produced_DLL_executed=True,
    neutral_resource_values=2, portable_PDB_associations=1, full_dependency_goal_complete=False), indent=2) + '\n')
print((out / 'execute.log').read_text(encoding='utf-8'))
