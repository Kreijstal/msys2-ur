"""Compile and audit 29 selected original Framework forwarding-target contracts."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as E

out, tools, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
selections = json.loads((here / 'inputs/target-selections.json').read_text())
key = out / 'ECMA.public.snk'; key.write_bytes(bytes.fromhex('00000000000000000400000000000000'))
assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == 'b77a5c561934e089'
mscorlib = prefix / 'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll'
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []; records = {}
policy = here / 'inputs/reference-build-policy.props'; suppressions = ['1701', '1702']
for node in E.parse(policy).iter('NoWarn'):
    suppressions += [s.removeprefix('CS') for s in re.split('[;,]', node.text.replace('$(NoWarn)', '')) if re.fullmatch(r'CS\d+', s)]
env = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
for name, types in selections.items():
    folder = out / name; folder.mkdir(); raw = folder / 'raw'; raw.mkdir(); ref = folder / 'ref'; ref.mkdir()
    source = here / 'generated' / (name + '-projection.cs')
    info = folder / 'AssemblyInfo.cs'; info.write_text('[assembly:System.Reflection.AssemblyVersion("4.0.0.0")]\n[assembly:System.Runtime.CompilerServices.ReferenceAssembly]\n')
    args = ['/nostdlib+', '/target:library', '/refonly', '/unsafe+', '/nullable:disable', '/langversion:latest', '/optimize+', '/deterministic+', '/warnaserror+', '/nowarn:' + ','.join(suppressions),
        '/publicsign+', '/keyfile:"' + key.as_posix() + '"', '/out:"' + (raw / (name + '.dll')).as_posix() + '"', '/reference:"' + mscorlib.as_posix() + '"',
        '"' + info.as_posix() + '"', '"' + source.as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
    rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
    run(name + '-compile', [dotnet, compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
    baseline = here / 'inputs/seed-baselines1' / (name + '-metadata.json')
    output = ref / (name + '.dll')
    run(name + '-port', [dotnet, tools / 'SeedMetadata/bin/Release/net8.0/SeedMetadata.dll', '--apply', raw / (name + '.dll'), baseline, output])
    run(name + '-metadata', [dotnet, tools / 'SeedMetadata/bin/Release/net8.0/SeedMetadata.dll', '--record', output, folder / 'metadata.json'])
    assert json.loads((folder / 'metadata.json').read_text()) == json.loads(baseline.read_text()), (name, 'declarative metadata')
    run(name + '-API', [dotnet, tools / 'Inspect/bin/Release/net8.0/Inspect.dll', folder / 'api.json', output])
    got = json.loads((folder / 'api.json').read_text())[name + '.dll']
    expected = json.loads((here / 'inputs/seed-baselines1' / (name + '-selected-api.json')).read_text())
    assert got['identity'] == expected['identity'], name
    missing, extra = set(expected['api']) - set(got['api']), set(got['api']) - set(expected['api'])
    assert not missing and not extra, (name, sorted(missing)[:10], sorted(extra)[:10])
    assert got['references'] == ['mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089'], (name, got['references'])
    assert any(a['type'] == 'System.Runtime.CompilerServices.ReferenceAssemblyAttribute' for a in got['attributes'])
    records[name] = dict(types=len(types), API_entries=len(got['api']), identity=got['identity'], source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), original_declarative_metadata_equal=True)
    print('PASS selected source Framework seed:', name, len(types), 'types,', len(got['api']), 'API entries and original declarative metadata', flush=True)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, seeds=records, compiler_NoWarn=suppressions, compiler_warnings_as_errors=True,
    compiler_policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(), selected_reference_types=sum(len(v) for v in selections.values()), required_forwarding_targets=29,
    full_Framework_reference_assemblies_built=False, compiler_references_only_not_runtime_implementations=True,
    published_DLLs_executed_or_compiler_references=False, publisher_method_bodies_copied=False, full_dependency_goal_complete=False), indent=2) + '\n')
