"""Verify NET6 metadata and consumers, including an independent NET8-only negative control."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

plan, build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
records = json.loads((build / 'results.json').read_text())['projects']
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs6 = sorted((build / 'ref/net6.0').glob('*.dll'))
refs8 = sorted((prefix / 'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll'))
assert len(refs6) == 137 and len(refs8) == 163
expected = {n: dict(assembly_version=r['assembly_version'], file_version=r['file_version'],
    public_key=bytes.fromhex((here / 'keys' / (r['strong_name_key'] + '.pubkey.hex')).read_text()).hex()) for n, r in records.items()}
(out / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n')
commands = []
def compile(label, source, references, exe=True):
    destination = out / (label + '.dll')
    args = ['/nostdlib+', '/target:' + ('exe' if exe else 'library'), '/nullable:enable', '/out:"' + native(destination) + '"']
    args += ['/reference:"' + native(p) + '"' for p in references] + ['"' + native(source) + '"']
    rsp = out / (label + '.rsp')
    rsp.write_text('\n'.join(args) + '\n')
    cmd = [host10, compiler, '-noconfig', '@' + native(rsp)]
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host10.parent), DOTNET_ROOT_X64=native(host10.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    if exe:
        (out / (label + '.runtimeconfig.json')).write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0', framework=dict(name='Microsoft.NETCore.App', version='8.0.31')))))
    return r.returncode, destination

def execute(label, cmd):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host8.parent), DOTNET_ROOT_X64=native(host8.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)

code, tool = compile('metadata-tool', here / 'AuditMetadata.cs', refs8)
assert code == 0
execute('metadata', [host8, tool, build / 'ref/net6.0', out / 'expected.json'])
metadata = json.loads((out / 'metadata.log').read_text(encoding='utf-8'))
(out / 'metadata-results.json').write_text(json.dumps(metadata, indent=2) + '\n')
code, consumer = compile('consumer', here / 'Consumer.cs', refs6)
assert code == 0
execute('consumer-runtime', [host8, consumer])
negative = out / 'Net8Only.cs'
negative.write_text('public static class Net8Only { public static object Clock => System.TimeProvider.System; }\n')
code, _ = compile('negative-net6', negative, refs6, False)
assert code != 0 and 'TimeProvider' in (out / 'negative-net6.log').read_text()
code, _ = compile('positive-net8', negative, refs8, False)
assert code == 0
(out / 'results.json').write_text(json.dumps(dict(commands=commands,
    core_reference_assemblies=137, all_original_metadata_and_reference_closure_checks_passed=True,
    actual_NET6_only_reference_consumer_compiled_and_executed_on_source_NET8=True,
    NET8_only_API_rejected_by_NET6_and_accepted_by_NET8_control=True,
    original_production_source_changes=0, compatibility_facades_built=False, complete_targeting_pack_built=False,
    original_NET6_runtime_host_built=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS 137 original NET6 core reference identities, closed metadata graph, real consumer and NET8-only negative control')
