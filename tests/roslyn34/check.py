"""Exercise the exact original compiler through its local bootstrap driver."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

bootstrap, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists()
out.mkdir()
dotnet = prefix / 'lib/dotnet/dotnet.exe'
driver = bootstrap / 'driver/bin/Release/net8.0/Driver.dll'
env = dict(os.environ, ROSLYN34_COMPILER_DIRECTORY=(bootstrap / 'runtime').as_posix())
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
records = []
def compile(name, text, language='8.0', encoding='utf-8', diagnostic=None):
    source = out / (name + '.cs')
    source.write_bytes(text.encode(encoding))
    args = ['/nologo', '/target:library', '/nostdlib+', '/warnaserror+', '/warn:4',
            '/langversion:' + language, '/deterministic+', '/debug:portable',
            '/out:"' + (out / (name + '.dll')).as_posix() + '"',
            '/pdb:"' + (out / (name + '.pdb')).as_posix() + '"']
    if encoding == 'cp932': args.append('/codepage:932')
    args += ['/reference:"' + p.as_posix() + '"' for p in refs]
    args.append('"' + source.as_posix() + '"')
    rsp = out / (name + '.rsp'); rsp.write_text('\n'.join(args) + '\n', encoding='utf-8')
    command = [str(dotnet), str(driver), '/noconfig', '@' + str(rsp)]
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '.log')).write_bytes(result.stdout)
    log = result.stdout.decode('utf-8', errors='replace')
    assert (result.returncode == 0 if diagnostic is None else result.returncode != 0 and diagnostic in log), (name, result.returncode, log)
    if diagnostic is None:
        assert (out / (name + '.dll')).is_file() and (out / (name + '.pdb')).is_file()
    else:
        assert not (out / (name + '.dll')).exists()
    records.append(dict(name=name, command=command, exit_code=result.returncode,
                        expected_diagnostic=diagnostic, log_sha256=hashlib.sha256(result.stdout).hexdigest()))
    print('PASS', name, 'exit', result.returncode, diagnostic or 'emitted assembly and portable PDB')

compile('FeatureFixture', '''#nullable enable
using System.IO;
public static class FeatureFixture {
 public static int Evaluate(string? text) {
  using var stream = new MemoryStream();
  return text switch { null => -1, { Length: var n } when n > 0 => n, _ => 0 };
 }
}
''')
compile('EncodingFixture', 'public static class EncodingFixture { public static string Name => "日本語"; }', encoding='cp932')
compile('NullableFailure', '#nullable enable\npublic class Bad { public int Length(string? value) => value.Length; }', diagnostic='CS8602')
compile('LanguageFailure', 'public class Bad { public int Value(int x) => x switch { 0 => 1, _ => 2 }; }', language='7.3', diagnostic='CS8370')
compile('SyntaxFailure', 'public class Broken {', diagnostic='CS1513')
script = '''$ErrorActionPreference='Stop'
$a=[Reflection.Assembly]::LoadFile('%FEATURE%')
$m=$a.GetType('FeatureFixture').GetMethod('Evaluate')
if($m.Invoke($null,[object[]]@('abcd')) -ne 4) {throw 'switch/property pattern result'}
if($m.Invoke($null,[object[]]@($null)) -ne -1) {throw 'nullable null pattern result'}
if($m.Invoke($null,[object[]]@('')) -ne 0) {throw 'empty switch arm result'}
$b=[Reflection.Assembly]::LoadFile('%ENCODING%')
$s=$b.GetType('EncodingFixture').GetProperty('Name').GetValue($null)
if((($s.ToCharArray() | ForEach-Object { [int]$_ }) -join ',') -ne '26085,26412,35486') {throw 'Shift-JIS source literal'}
'PASS emitted C#8 switch/property patterns, nullable branches, using declaration and original CodePages Shift-JIS source decoding execute on source NET8'
'''.replace('%FEATURE%', (out / 'FeatureFixture.dll').as_posix()).replace('%ENCODING%', (out / 'EncodingFixture.dll').as_posix())
ps = out / 'Execute.ps1'; ps.write_text(script, encoding='utf-8')
command = [str(prefix / 'bin/pwsh.exe'), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ps)]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'execute.log').write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
records.append(dict(name='execute', command=command, exit_code=result.returncode, log_sha256=hashlib.sha256(result.stdout).hexdigest()))
(out / 'results.json').write_text(json.dumps(dict(checks=records, original_NETCore21_runtime_executed=False,
    runtime='installed source NET8', original_Toolset_executables_verified=False,
    source_NS2_reference_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in refs}), indent=2) + '\n')
print(result.stdout.decode('utf-8', errors='replace'))
