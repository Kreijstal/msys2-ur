"""Exercise the source analyzer in Csc5.3 with positive, nullable, added and stale API fixtures."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
native = lambda p: Path(p).resolve().as_posix()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
assert len(refs) == 167
analyzer = build / 'bin/Microsoft.CodeAnalysis.PublicApiAnalyzers.dll'
source = '#nullable enable\npublic static class Fixture { public static string Echo(string value) => value; }\n'
annotated = '#nullable enable\nFixture\nstatic Fixture.Echo(string! value) -> string!\n'
cases = {
    'exact': (source, annotated, 0),
    'legacy-oblivious': (source, '#nullable enable\nFixture\n~static Fixture.Echo(string value) -> string\n', 1),
    'nullable-changed': (source, '#nullable enable\nFixture\nstatic Fixture.Echo(string? value) -> string!\n', 1),
    'public-member-added': (source.replace(' => value;', ' => value; public static void Extra() {}'), annotated, 1),
    'stale-member': (source, annotated + 'static Fixture.Old() -> void\n', 1),
}
records = []
for label, (body, baseline, expected) in cases.items():
    folder = out / label
    folder.mkdir()
    (folder / 'Fixture.cs').write_text(body)
    (folder / 'PublicAPI.Shipped.txt').write_text(baseline)
    (folder / 'PublicAPI.Unshipped.txt').write_text('#nullable enable\n')
    args = ['/nostdlib+', '/target:library', '/nullable:enable', '/warnaserror+',
        '/out:"' + native(folder / 'Fixture.dll') + '"', '/analyzer:"' + native(analyzer) + '"']
    args += ['/reference:"' + native(p) + '"' for p in refs]
    args += ['/additionalfile:"' + native(folder / n) + '"' for n in ['PublicAPI.Shipped.txt', 'PublicAPI.Unshipped.txt']]
    args += ['"' + native(folder / 'Fixture.cs') + '"']
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    cmd = [host, compiler, '-noconfig', '@' + native(rsp)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ,
        DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    (folder / 'compile.log').write_text(r.stdout)
    assert not any(code in r.stdout for code in ['AD0001', 'CS8032', 'CS9057']), (label, r.stdout)
    assert r.returncode == expected, (label, r.returncode, expected, r.stdout)
    if label == 'legacy-oblivious':
        assert 'RS0036' in r.stdout and 'RS0016' not in r.stdout and 'RS0017' not in r.stdout, r.stdout
    elif expected:
        assert 'RS0016' in r.stdout or 'RS0017' in r.stdout, (label, r.stdout)
    records.append(dict(case=label, command=[str(p) for p in cmd], exit_code=r.returncode,
        expected_exit_code=expected, analyzer_sha256=hashlib.sha256(analyzer.read_bytes()).hexdigest()))
    print('PASS', label, r.returncode, flush=True)
(out / 'results.json').write_text(json.dumps(dict(cases=records, actual_source_analyzer_executed_by_Csc53=True,
    legacy_oblivious_and_explicit_nullable_policy_verified=True, added_and_stale_public_APIs_rejected=True,
    analyzer_load_failures_and_exceptions_rejected=True, full_upstream_suite_run=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
