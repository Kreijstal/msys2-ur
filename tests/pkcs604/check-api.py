"""Compare both NET6 producers with the unchanged original NET6 reference source."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, xml.etree.ElementTree as E

plan, build, reference_root, out = (Path(p).resolve() for p in sys.argv[1:5])
cached_contract = Path(sys.argv[5]).resolve() if len(sys.argv) == 6 else None
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = Path(json.loads((plan / 'source-inputs.json').read_text())['source_root'])
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
toolrefs = sorted((prefix / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
refs = sorted((reference_root / 'build/ref/net6.0').glob('*.dll'))
assert len(toolrefs) == 167 and len(refs) == 137
for n in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']:
    shutil.copyfile(compiler / (n + '.dll'), out / (n + '.dll'))
commands = []
def compile(label, args):
    rsp = out / (label + '.rsp')
    rsp.write_text('\n'.join(args) + '\n')
    cmd = [host, compiler / 'csc.dll', '-noconfig', '@' + native(rsp)]
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=240)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
compile('tool', ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(out / 'Api.dll') + '"'] +
    ['/reference:"' + native(p) + '"' for p in toolrefs + [out / (n + '.dll') for n in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']]] +
    ['"' + native(here / 'CompareApi.cs') + '"'])
(out / 'Api.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0', framework=dict(name='Microsoft.NETCore.App', version='10.0.5')))))
name = 'System.Security.Cryptography.Pkcs'
project = source / 'src/libraries' / name / 'ref' / (name + '.csproj')
files = []
for item in E.parse(project).findall('.//Compile'):
    condition = item.get('Condition')
    assert condition in ["'$(TargetFramework)' != 'net461'", "'$(TargetFramework)' == 'net461'", "$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'netstandard2.1'))"]
    if condition != "'$(TargetFramework)' == 'net461'":
        files.append(project.parent / item.get('Include'))
assert len(files) == 2 and all(p.is_file() for p in files)
folder = out / 'contract'
folder.mkdir()
key = folder / 'public.snk'
key.write_bytes(bytes.fromhex((here / 'Microsoft.pubkey.hex').read_text()))
info = folder / 'AssemblyInfo.cs'
info.write_text('[assembly:System.Reflection.AssemblyVersion("6.0.0.0")]\n')
contract = folder / (name + '.dll')
compile('contract', ['/nostdlib+', '/target:library', '/refonly', '/nullable:enable', '/langversion:preview', '/features:strict,nullablePublicOnly',
    '/publicsign+', '/keyfile:"' + native(key) + '"', '/out:"' + native(contract) + '"',
    '/define:NET;NETCOREAPP;NET6_0;NET5_0_OR_GREATER;NET6_0_OR_GREATER'] +
    ['/reference:"' + native(p) + '"' for p in refs] + ['"' + native(p) + '"' for p in files + [info]])
fixtures = out / 'fixtures'
fixtures.mkdir()
base = 'public class Ancestor { public virtual string? Copy(string? v) => v; } public class Base : Ancestor { public override string? Copy(string? v) => v; } '
cases = {
    'reference': base + 'public sealed class Derived : Base {}',
    'equivalent-override': base + 'public sealed class Derived : Base { public override string? Copy(string? v) => v; }',
    'new-public-member': base + 'public sealed class Derived : Base { public override string? Copy(string? v) => v; public void Extra() {} }',
    'changed-nullable-override': base + 'public sealed class Derived : Base { public override string Copy(string? v) => v!; }',
}
for label, code in cases.items():
    p = fixtures / (label + '.cs')
    p.write_text(code + '\n')
    compile('fixture-' + label, ['/nostdlib+', '/target:library', '/nullable:enable', '/out:"' + native(fixtures / (label + '.dll')) + '"'] +
        ['/reference:"' + native(p) + '"' for p in refs] + ['"' + native(p) + '"'])
fixture_results = []
for label, expected_code in [('equivalent-override', 0), ('new-public-member', 1), ('changed-nullable-override', 1)]:
    cmd = [host, out / 'Api.dll', fixtures / 'reference.dll', fixtures / (label + '.dll'), reference_root / 'build/ref/net6.0', fixtures / (label + '.json')]
    with (fixtures / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    assert r.returncode == expected_code, (label, r.returncode, expected_code)
    fixture_results.append(dict(case=label, exit_code=r.returncode, expected_exit_code=expected_code))
records = {}
for label in ['windows', 'portable'] + (['cached-reference'] if cached_contract else []):
    produced = cached_contract if label == 'cached-reference' else build / label / 'bin' / (name + '.dll')
    cmd = [host, out / 'Api.dll', contract, produced, reference_root / 'build/ref/net6.0', out / (label + '-comparison.json')]
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    records[label] = dict(exit_code=r.returncode, implementation_sha256=sha(produced), comparison=json.loads((out / (label + '-comparison.json')).read_text()))
    print(label, (out / (label + '.log')).read_text(encoding='utf-8'), flush=True)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, original_contract_source_sha256={p.relative_to(source).as_posix(): sha(p) for p in files},
    reference_contract_sha256=sha(contract), inherited_override_checker_positive_and_negative_fixtures=fixture_results,
    projects=records, full_custom_attribute_and_constraint_comparison_performed=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
raise SystemExit(0 if all(p['exit_code'] == 0 for p in records.values()) else 1)
