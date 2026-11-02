"""Check NuGet framework semantics and inventory actual source restore gaps."""
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
package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == 'netstandard.library.1.6.1.nupkg')
with zipfile.ZipFile(package) as z:
    assert not any(p.endswith(('.dll', '.exe', '_._')) for p in z.namelist())
    for name, digest in policy['original_nonmetadata_files'].items(): assert hashlib.sha256(z.read(name)).hexdigest() == digest
tool = out / 'tool'; tool.mkdir()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='Check', UseAppHost='false', EnableDefaultItems='false',
    EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true').items(): E.SubElement(props, n).text = v
items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(here / 'inputs/Check.cs').as_posix())
sdk = prefix / 'lib/dotnet/sdk/8.0.131'
references = {}
for name in ['NuGet.Packaging', 'NuGet.Frameworks', 'NuGet.Versioning', 'NuGet.Common']:
    path = sdk / (name + '.dll'); assert path.is_file()
    E.SubElement(items, 'Reference', Include=name, HintPath=path.as_posix())
    references[name] = hashlib.sha256(path.read_bytes()).hexdigest()
E.indent(tree); E.ElementTree(tree).write(tool / 'Check.csproj', encoding='utf-8', xml_declaration=True)
(tool / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
environment = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command, required=True):
    result = subprocess.run([str(p) for p in command], env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    if required: assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
    return result
run('tool-build', [dotnet, 'build', tool / 'Check.csproj', '-c', 'Release', '--configfile', tool / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
result = run('semantics', [dotnet, tool / 'bin/Release/net8.0/Check.dll', package, here / 'inputs/provenance.json'])
print(result.stdout.decode('utf-8', errors='replace'))
installed = (prefix / 'lib/dotnet/library-packs').resolve()
same = feed.as_posix().casefold() == installed.as_posix().casefold()
config = E.Element('configuration'); sources = E.SubElement(config, 'packageSources'); E.SubElement(sources, 'clear')
E.SubElement(sources, 'add', key='candidate', value=feed.as_posix())
if not same: E.SubElement(sources, 'add', key='installed', value=installed.as_posix())
mapping = E.SubElement(config, 'packageSourceMapping'); candidate = E.SubElement(mapping, 'packageSource', key='candidate')
E.SubElement(candidate, 'package', pattern='NETStandard.Library')
E.SubElement(candidate if same else E.SubElement(mapping, 'packageSource', key='installed'), 'package', pattern='*')
E.indent(config); E.ElementTree(config).write(out / 'NuGet.config', encoding='utf-8', xml_declaration=True)
restores = {}
for framework in ['netstandard1.0', 'netstandard1.1', 'netstandard1.2', 'netstandard1.3']:
    folder = out / framework; folder.mkdir()
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(project, 'PropertyGroup')
    for n, v in dict(TargetFramework=framework, EnableDefaultItems='false', DisableImplicitFrameworkReferences='true', NuGetAudit='false', TreatWarningsAsErrors='true').items(): E.SubElement(pg, n).text = v
    E.SubElement(E.SubElement(project, 'ItemGroup'), 'PackageReference', Include='NETStandard.Library', Version='[1.6.1]')
    E.indent(project); E.ElementTree(project).write(folder / 'Probe.csproj', encoding='utf-8', xml_declaration=True)
    result = run(framework + '-restore', [dotnet, 'restore', folder / 'Probe.csproj', '--configfile', out / 'NuGet.config', '-v:minimal'], required=False)
    assets = json.loads((folder / 'obj/project.assets.json').read_text())
    assert 'NETStandard.Library/1.6.1' in assets['libraries']
    diagnostics = assets.get('logs', [])
    assert not any(d.get('code') == 'NU1603' and d.get('libraryId', '').lower() == 'netstandard.library' for d in diagnostics)
    restores[framework] = dict(exit_code=result.returncode, diagnostics=diagnostics)
    print(framework, 'restore exit', result.returncode, '; diagnostic codes', sorted({d.get('code') for d in diagnostics}))
cached = out / 'cache/netstandard.library/1.6.1/netstandard.library.1.6.1.nupkg'
assert cached.read_bytes() == package.read_bytes()
(out / 'results.json').write_text(json.dumps(dict(commands=commands, package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
    source_SDK_NuGet_reference_hashes=references, four_original_groups_and_128_edges_verified=True,
    six_original_framework_selection_checks_passed=True, exact_fresh_cached_archive_verified=True,
    restores=restores, full_framework_implementation_graph_complete=all(r['exit_code'] == 0 for r in restores.values()),
    historical_runtime_execution_verified=False, full_dependency_goal_complete=False), indent=2) + '\n')
