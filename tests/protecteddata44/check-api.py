"""Compare unchanged ProtectedData4.4 reference source to the produced implementation."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, xml.etree.ElementTree as E

build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
toolrefs = sorted((prefix / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(toolrefs) == 167 and len(refs) == 113
source = Path(json.loads((build / 'results.json').read_text())['source_root'])
name = 'System.Security.Cryptography.ProtectedData'
project = source / 'src' / name / 'ref' / (name + '.csproj')
tree = E.parse(project)
ns = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}
files = [project.parent / c.get('Include') for c in tree.findall('.//m:Compile', ns)]
assert len(files) == 1 and files[0].is_file()
commands = []

def run(label, args):
    rsp = out / (label + '.rsp')
    rsp.write_text('\n'.join(args) + '\n')
    cmd = [host, compiler / 'csc.dll', '-noconfig', '@' + native(rsp)]
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)

for assembly in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']:
    shutil.copyfile(compiler / (assembly + '.dll'), out / (assembly + '.dll'))
run('tool', ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(out / 'Api.dll') + '"'] +
    ['/reference:"' + native(p) + '"' for p in toolrefs + [out / (n + '.dll') for n in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']]] +
    ['"' + native(here / 'CompareApi.cs') + '"'])
(out / 'Api.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0', framework=dict(name='Microsoft.NETCore.App', version='10.0.5')))))
key = out / 'public.snk'
key.write_bytes(bytes.fromhex((here / 'Microsoft.pubkey.hex').read_text()))
info = out / 'AssemblyInfo.cs'
info.write_text('[assembly:System.Reflection.AssemblyVersion("4.0.2.0")]\n')
contract = out / 'ref' / (name + '.dll')
contract.parent.mkdir()
run('contract', ['/nostdlib+', '/target:library', '/nullable:disable', '/refonly', '/publicsign+',
    '/keyfile:"' + native(key) + '"', '/out:"' + native(contract) + '"'] +
    ['/reference:"' + native(p) + '"' for p in refs] + ['"' + native(p) + '"' for p in files + [info]])
reference_dir = out / 'references'
reference_dir.mkdir()
for ref in refs:
    shutil.copyfile(ref, reference_dir / ref.name)
cmd = [host, out / 'Api.dll', contract, build / 'bin' / (name + '.dll'), reference_dir, out / 'comparison.json']
with (out / 'compare.log').open('w', encoding='utf-8') as log:
    r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
record = dict(commands=commands, exit_code=r.returncode, comparison=json.loads((out / 'comparison.json').read_text()),
    reference_contract_sha256=sha(contract), implementation_sha256=sha(build / 'bin' / (name + '.dll')),
    original_contract_source_sha256={p.relative_to(source).as_posix(): sha(p) for p in files},
    original_reference_project_sha256=sha(project), comparator_sha256=sha(here / 'CompareApi.cs'),
    full_custom_attribute_and_generic_constraint_comparison_performed=False, full_dependency_goal_complete=False)
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
print((out / 'compare.log').read_text(encoding='utf-8'))
raise SystemExit(r.returncode)
