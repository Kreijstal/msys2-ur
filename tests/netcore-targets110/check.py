"""Check original Targets graph semantics and exact fresh package consumption."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
policy = json.loads((here / 'inputs/provenance.json').read_text())
package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == 'microsoft.netcore.targets.1.1.0.nupkg')
with zipfile.ZipFile(package) as z:
    assert not any(n.endswith(('.dll', '.exe')) for n in z.namelist())
    assert {n for n in z.namelist() if n.endswith('_._')} == {policy['original_empty_marker']}
    assert z.read(policy['original_empty_marker']) == b''
    for n, digest in policy['original_data_sha256'].items(): assert hashlib.sha256(z.read(n)).hexdigest() == digest
    (out / 'runtime.json').write_bytes(z.read('runtime.json'))
platform_package = prefix / 'lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.0.nupkg'
with zipfile.ZipFile(platform_package) as z: (out / 'platform-runtime.json').write_bytes(z.read('runtime.json'))
tool = out / 'tool'; tool.mkdir(); tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='Check', UseAppHost='false', EnableDefaultItems='false',
    EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true').items(): E.SubElement(props, n).text = v
items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(here / 'inputs/Check.cs').as_posix())
references = {}
for n in ['NuGet.Packaging', 'NuGet.Frameworks', 'NuGet.Versioning', 'NuGet.Common', 'Newtonsoft.Json']:
    p = prefix / 'lib/dotnet/sdk/8.0.131' / (n + '.dll'); assert p.is_file()
    E.SubElement(items, 'Reference', Include=n, HintPath=p.as_posix()); references[n] = hashlib.sha256(p.read_bytes()).hexdigest()
E.indent(tree); E.ElementTree(tree).write(tool / 'Check.csproj', encoding='utf-8', xml_declaration=True)
(tool / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
env = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command):
    result = subprocess.run([str(p) for p in command], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
    return result
run('build', [dotnet, 'build', tool / 'Check.csproj', '-c', 'Release', '--configfile', tool / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
result = run('graph', [dotnet, tool / 'bin/Release/net8.0/Check.dll', out / 'runtime.json', out / 'platform-runtime.json'])
print(result.stdout.decode('utf-8', errors='replace'))
config = E.Element('configuration'); sources = E.SubElement(config, 'packageSources'); E.SubElement(sources, 'clear')
E.SubElement(sources, 'add', key='source', value=feed.as_posix()); E.indent(config)
E.ElementTree(config).write(out / 'NuGet.config', encoding='utf-8', xml_declaration=True)
for framework in ['netstandard1.0', 'netstandard1.3', 'net8.0']:
    folder = out / framework; folder.mkdir(); project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(project, 'PropertyGroup')
    for n, v in dict(TargetFramework=framework, EnableDefaultItems='false', DisableImplicitFrameworkReferences='true', NuGetAudit='false', TreatWarningsAsErrors='true').items(): E.SubElement(pg, n).text = v
    E.SubElement(E.SubElement(project, 'ItemGroup'), 'PackageReference', Include='Microsoft.NETCore.Targets', Version='[1.1.0]')
    E.indent(project); E.ElementTree(project).write(folder / 'Probe.csproj', encoding='utf-8', xml_declaration=True)
    run(framework + '-restore', [dotnet, 'restore', folder / 'Probe.csproj', '--configfile', out / 'NuGet.config', '-v:minimal'])
    assets = json.loads((folder / 'obj/project.assets.json').read_text()); assert not assets.get('logs')
    assert 'Microsoft.NETCore.Targets/1.1.0' in assets['libraries']
cached = out / 'cache/microsoft.netcore.targets/1.1.0/microsoft.netcore.targets.1.1.0.nupkg'
assert cached.read_bytes() == package.read_bytes()
(out / 'results.json').write_text(json.dumps(dict(commands=commands, package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
    source_NuGet_tool_references=references, source_Platforms110_archive_sha256=hashlib.sha256(platform_package.read_bytes()).hexdigest(),
    original_runtime_rows=22, original_runtime_dependency_edges=97, original_support_profiles=14,
    all_NuGet_runtime_dependency_ranges_and_merged_platform_lookups_verified=True, exact_fresh_archive_cache_verified=True,
    fresh_package_restores=['netstandard1.0','netstandard1.3','net8.0'], original_single_marker_preserved=True,
    implementation_binaries=0, runtime_packages_or_historical_runtimes_verified=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS three fresh exact Targets1.1 restores and archive cache bytes; original single marker; zero implementation payloads')
