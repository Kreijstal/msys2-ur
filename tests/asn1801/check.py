"""Compile with NET8 contracts and execute the exact produced ASN.1 DLL on NET8/NET10."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, xml.etree.ElementTree as E

plan, build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = [p for p in (prefix / 'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll') if p.name != 'System.Formats.Asn1.dll']
assert len(refs) == 162
produced = build / 'bin/System.Formats.Asn1.dll'
args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(out / 'Check.dll') + '"']
args += ['/reference:"' + native(p) + '"' for p in refs + [produced]] + ['"' + native(here / 'Check.cs') + '"']
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
(out / 'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0', framework=dict(name='Microsoft.NETCore.App', version='8.0.31')))))
record = json.loads((build / 'results.json').read_text())['projects'][0]
documentation = build / 'bin/System.Formats.Asn1.xml'
assert hashlib.sha256(documentation.read_bytes()).hexdigest() == record['original_documentation']['sha256']
members = {n.get('name') for n in E.parse(documentation).findall('members/member')}
required_documentation = {'T:System.Formats.Asn1.AsnContentException',
    'M:System.Formats.Asn1.AsnContentException.#ctor',
    'M:System.Formats.Asn1.AsnContentException.#ctor(System.String)',
    'M:System.Formats.Asn1.AsnContentException.#ctor(System.String,System.Exception)',
    'M:System.Formats.Asn1.AsnContentException.#ctor(System.Runtime.Serialization.SerializationInfo,System.Runtime.Serialization.StreamingContext)',
    'T:System.Formats.Asn1.AsnWriter.Scope', 'M:System.Formats.Asn1.AsnWriter.Scope.Dispose'}
assert required_documentation <= members
commands = []
for label, host, cmd in [
    ('compile', host10, [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')]),
    ('net8', host8, [host8, out / 'Check.dll', produced]),
    ('net10', host10, [host10, '--fx-version', '10.0.5', out / 'Check.dll', produced])]:
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
(out / 'results.json').write_text(json.dumps(dict(commands=commands,
    produced_sha256=hashlib.sha256(produced.read_bytes()).hexdigest(),
    original_NET8_compiler_references_preserved=True, produced_DLL_executed_on_NET8_and_NET10=True,
    isolated_load_path_assembly_key_version_file_version_and_TFA_verified=True,
    DER_BER_CER_Unicode_OID_integer_bit_octet_sorting_time_bounds_and_malformed_data_passed=True,
    original_Intellisense_XML_hash_and_seven_non_inline_documented_members_verified=True,
    original_documentation_members=len(members), full_upstream_test_suite_run=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS original NET8 source ASN.1 on NET8/NET10: isolated exact identity, DER/BER/CER, Unicode and malformed data')
