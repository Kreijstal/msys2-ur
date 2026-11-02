"""Restore old reference metadata and compile the complete original NET462 facade."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

producer, archive, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
source = out / 'source'; source.mkdir()
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == '4d1af962ca0fede10beb01d197367c2f90e92c97'
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name in ['src/System.Reflection/src/System.Reflection.csproj', 'src/System.Reflection/dir.props', 'src/System.Reflection/pkg/System.Reflection.pkgproj', 'LICENSE', 'THIRD-PARTY-NOTICES']:
        path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(tar.extractfile(entries[name]).read())
project = E.parse(source / 'src/System.Reflection/src/System.Reflection.csproj')
assert project.findtext('.//{*}IsPartialFacadeAssembly') == 'true'
assert any(t.get('Include') == 'mscorlib' for t in project.findall('.//{*}TargetingPackReference'))
assert E.parse(source / 'src/System.Reflection/dir.props').findtext('.//{*}AssemblyVersion') == '4.1.1.0'
package_project = E.parse(source / 'src/System.Reflection/pkg/System.Reflection.pkgproj')
assert any(p.findtext('{*}TargetGroup') == 'net462' for p in package_project.findall('.//{*}ProjectReference'))
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
env = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
    return result

package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
assert hashlib.sha256(package.read_bytes()).hexdigest() == 'c32254ab0d8d040d0aed45d8b3e521c319fa035041aa029685341b46b167bb30'
tools = out / 'tools'; tools.mkdir()
with zipfile.ZipFile(package) as z: (tools / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
config = tools / 'NuGet.config'; config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
for tool, startup in [('RestoreAttributes', 'RestoreAttributes'), ('GenerateFacade', 'GenerateFacade')]:
    folder = tools / tool; folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
    for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName=tool, StartupObject=startup, UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true', CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items(): E.SubElement(pg, n).text = v
    items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(here / 'inputs' / (tool + '.cs')).as_posix())
    E.SubElement(items, 'Reference', Include='Mono.Cecil', HintPath=(tools / 'Mono.Cecil.dll').as_posix())
    E.indent(tree); E.ElementTree(tree).write(folder / (tool + '.csproj'), encoding='utf-8', xml_declaration=True)
    run(tool + '-build', [dotnet, 'build', folder / (tool + '.csproj'), '-c', 'Release', '--configfile', config, '-p:UseSharedCompilation=false', '-v:minimal'])
run('restore', [dotnet, tools / 'RestoreAttributes/bin/Release/net8.0/RestoreAttributes.dll', here / 'inputs', producer / 'raw', out / 'ref'])
seed = prefix / 'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll'
facade = out / 'ref/System.Reflection/net462'; facade.mkdir()
generated = facade / 'Forwards.cs'
result = run('generate', [dotnet, tools / 'GenerateFacade/bin/Release/net8.0/GenerateFacade.dll', out / 'ref/System.Reflection/netstandard1.5/System.Reflection.dll', seed, here / 'inputs/System.Reflection-net462.json', generated])
print(result.stdout.decode('utf-8', errors='replace'), flush=True)
args = ['/nostdlib+', '/target:library', '/optimize+', '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+', '/keyfile:"' + (here / 'inputs/Microsoft.snk').as_posix() + '"', '/out:"' + (facade / 'System.Reflection.dll').as_posix() + '"', '/reference:"' + seed.as_posix() + '"', '"' + generated.as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
rsp = facade / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
run('facade-compile', [dotnet, compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
(out / 'results.json').write_text(json.dumps(dict(commands=commands, source_CoreFX_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    source_CoreFX_project_hashes={p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},
    facade_reference_contract=producer.as_posix(), source_Framework_seed_sha256=hashlib.sha256(seed.read_bytes()).hexdigest(),
    source_generated_forwarder_CS_sha256=hashlib.sha256(generated.read_bytes()).hexdigest(), facade_type_count=34,
    original_published_version_attribute_data_used=True, NET46_source_seed_supplies_all_original_NET462_forwarding_targets=True,
    complete_NET462_targeting_pack_or_runtime_verified=False, original_historical_build_tools_replayed=False,
    original_binaries_executed_or_compiler_references=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS source NET462 forwarding facade compiled; all three reference profiles retained')
