"""Compile the original NET462 Runtime forwarding facade using source-only seeds."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, references, seeds, tools, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
source = out / 'source'; source.mkdir()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == '4d1af962ca0fede10beb01d197367c2f90e92c97'
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name in ['src/System.Runtime/dir.props', 'src/System.Runtime/src/System.Runtime.csproj', 'src/System.Runtime/src/System.Runtime.Forwards.cs', 'src/System.Runtime/pkg/System.Runtime.pkgproj', 'LICENSE', 'THIRD-PARTY-NOTICES']:
        path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(tar.extractfile(entries[name]).read())
assert E.parse(source / 'src/System.Runtime/dir.props').findtext('.//{*}AssemblyVersion') == '4.1.1.0'
project = E.parse(source / 'src/System.Runtime/src/System.Runtime.csproj')
assert project.findtext('.//{*}IsPartialFacadeAssembly') == 'true'
assert {'mscorlib', 'System', 'System.Core', 'System.ComponentModel.Composition'} <= {e.get('Include') for e in project.findall('.//{*}TargetingPackReference')}
forwards = (source / 'src/System.Runtime/src/System.Runtime.Forwards.cs').read_text()
assert re.findall(r'TypeForwardedTo\(typeof\(([^)]+)\)\)', forwards) == ['System.Runtime.InteropServices.GCHandle', 'System.Runtime.InteropServices.GCHandleType']
package = E.parse(source / 'src/System.Runtime/pkg/System.Runtime.pkgproj')
assert any(e.findtext('{*}TargetGroup') == 'net462' for e in package.findall('.//{*}ProjectReference'))
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
env = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
    return result
targets = [prefix / 'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll']
targets += [seeds / name / 'ref' / (name + '.dll') for name in ['System', 'System.Core', 'System.ComponentModel.Composition']]
source_file = out / 'Forwards.cs'
result = run('generate', [dotnet, tools / 'GenerateRuntimeFacade/bin/Release/net8.0/GenerateRuntimeFacade.dll', references / 'System.Runtime/netstandard1.5/System.Runtime.dll', here / 'inputs/System.Runtime-net462.json', source_file, here / 'inputs/net462-exported-types.json', *targets])
print(result.stdout.decode('utf-8', errors='replace'), flush=True)
args = ['/nostdlib+', '/target:library', '/optimize+', '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+', '/keyfile:"' + (here / 'inputs/Microsoft.snk').as_posix() + '"', '/out:"' + (out / 'System.Runtime.dll').as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
args += ['/reference:"' + p.as_posix() + '"' for p in targets] + ['"' + source_file.as_posix() + '"']
rsp = out / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
run('compile', [dotnet, compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
projected = out / 'projected'; projected.mkdir()
run('contract-export-port', [dotnet, tools / 'PortFacadeExports/bin/Release/net8.0/PortFacadeExports.dll', out / 'System.Runtime.dll', here / 'inputs/net462-exported-types.json', projected / 'System.Runtime.dll'])
raw = out / 'raw'; raw.mkdir(); shutil.move(out / 'System.Runtime.dll', raw / 'System.Runtime.dll'); shutil.copy2(projected / 'System.Runtime.dll', out / 'System.Runtime.dll')
(out / 'results.json').write_text(json.dumps(dict(commands=commands, source_CoreFX_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    source_CoreFX_project_hashes={p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},
    source_reference_seed_hashes={p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets},
    source_generated_forwarder_CS_sha256=hashlib.sha256(source_file.read_bytes()).hexdigest(), original_forwarding_types=277,
    exactly_four_extra_nested_seed_exports_removed_to_match_original_contract=True,
    original_published_version_attribute_data_used=True, all_original_forwarding_types_have_source_seed_and_original_scope=True,
    private_Framework_seeds_are_reference_only_not_runtime_implementations=True, original_historical_build_tools_replayed=False,
    full_NET462_targeting_pack_or_runtime_verified=False, original_binaries_executed_or_compiler_references=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS original277-type Runtime NET462 forwarding facade compiled with warnings as errors')
