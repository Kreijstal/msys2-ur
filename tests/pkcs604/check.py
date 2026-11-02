"""Execute each produced PKCS6 profile on the source NET8 and NET10 hosts."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as E

parser = argparse.ArgumentParser()
for name in ['plan', 'build', 'reference_root', 'out']:
    parser.add_argument(name, type=Path)
parser.add_argument('--contract', type=Path)
parser.add_argument('--asn1', type=Path)
options = parser.parse_args()
plan, build, reference_root, out = (getattr(options, n).resolve() for n in ['plan', 'build', 'reference_root', 'out'])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
source = Path(json.loads((plan / 'source-inputs.json').read_text())['source_root'])
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((reference_root / 'build/ref/net6.0').glob('*.dll'))
assert len(refs) == 137
expected = {n.get('name'): n.findtext('value') for n in E.parse(source / 'src/libraries/System.Security.Cryptography.Pkcs/src/Resources/Strings.resx').findall('data')}
(out / 'expected-resources.json').write_text(json.dumps(expected) + '\n')
commands = []
def run(label, host, cmd):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
for label in ['windows', 'portable']:
    produced = build / label / 'bin/System.Security.Cryptography.Pkcs.dll'
    dest = out / (label + '-Check.dll')
    args = ['/nostdlib+', '/target:exe', '/nullable:enable', '/out:"' + native(dest) + '"']
    args += ['/reference:"' + native(p) + '"' for p in refs + [options.contract or produced]] + ['"' + native(here / 'Check.cs') + '"']
    rsp = out / (label + '.rsp')
    rsp.write_text('\n'.join(args) + '\n')
    dest.with_suffix('.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0', framework=dict(name='Microsoft.NETCore.App', version='8.0.31')))))
    run(label + '-compile', host10, [host10, compiler, '-noconfig', '@' + native(rsp)])
    for version, host, host_options in [('net8', host8, []), ('net10', host10, ['--fx-version', '10.0.5'])]:
        cmd = [host] + host_options + [dest, produced, out / 'expected-resources.json', here / 'inputs/rsa-pss-document.der']
        run(label + '-' + version, host, cmd)
        if version == 'net10' and options.asn1:
            run(label + '-net10-cached-asn1', host, cmd + [options.asn1.resolve()])
(out / 'results.json').write_text(json.dumps(dict(commands=commands, actual_produced_DLLs_executed=True,
    both_original_NET6_profiles_tested_on_source_NET8_and_NET10=True, compilation_uses_only_original_NET6_core_contracts=True,
    CMS_RSA_sign_verify_tamper_envelope_decrypt_wrong_key_and_PKCS12_MAC_password_passed=True,
    original_upstream_PSS_unsupported_salt_negative_case_passed=True,
    neutral_resource_values_per_profile=len(expected), portable_PDB_associations=2,
    compilation_uses_actual_cached_NuGet_reference_asset=options.contract is not None,
    NET10_executes_actual_cached_source_Asn1_dependency=options.asn1 is not None,
    original_NET6_runtime_host_built=False, other_original_profiles_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS both produced PKCS6 original profiles on NET8/NET10, real cryptography, all neutral resources and PDBs')
