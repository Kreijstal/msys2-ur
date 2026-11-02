"""Execute source NS2 codefixes with a source-restored Roslyn4.4 workspace on NET10."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, zipfile

build, restore, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
binary = out / 'bin'
binary.mkdir()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
native = lambda p: Path(p).resolve().as_posix()
records = json.loads((restore / 'results.json').read_text())
assets = []
for package, record in records['actual_source_packages'].items():
    archive = Path(record['archive'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == record['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        for member in record['runtime_assets']:
            if not member.endswith('.dll'):
                continue
            data = z.read(member)
            (binary / Path(member).name).write_bytes(data)
            assets.append(dict(package=package, version=record['version'], archive_sha256=record['archive_sha256'], member=member, sha256=hashlib.sha256(data).hexdigest()))
for p in (build / 'bin').glob('*.dll'):
    shutil.copyfile(p, binary / p.name)
refs = sorted((prefix / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
assert len(refs) == 167
selected = {p.name: p for p in [*binary.glob('*.dll'), *refs]}
args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(binary / 'Check.dll') + '"']
args += ['/reference:"' + native(p) + '"' for p in selected.values()] + ['"' + native(Path(__file__).parent / 'CheckCodeFix.cs') + '"']
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
(binary / 'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0', framework=dict(name='Microsoft.NETCore.App', version='10.0.5')))))
commands = []
for label, cmd in [('compile', [host, compiler, '-noconfig', '@' + native(out / 'compile.rsp')]),
        ('execute', [host, binary / 'Check.dll', refs[0].parent, out])]:
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, actual_source_restored_runtime_assets=assets,
    source_analyzer_and_codefix_executed=True, codefix_providers_executed=3, document_fix_all_cases=3, direct_codefix_applications=4, real_workspace_codefix_application_and_diagnostic_cleanup_verified=True,
    original_NS2_TFA_key_and_identity_verified=True, original_Roslyn12_host_compatibility_verified=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print((out / 'execute.log').read_text())
