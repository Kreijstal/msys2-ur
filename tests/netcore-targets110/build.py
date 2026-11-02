"""Port original Targets1.1 runtime/support metadata; no implementation DLLs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
policy = json.loads((here / 'inputs/provenance.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == policy['source_archive_sha256']
selected = ['pkg/Microsoft.NETCore.Targets/Microsoft.NETCore.Targets.pkgproj', 'pkg/Microsoft.NETCore.Targets/runtime.json',
            'pkg/NETStandard.Library/NETStandard.Library.packages.targets', 'LICENSE', 'THIRD-PARTY-NOTICES']
hashes = {}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == policy['source_commit']
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name in selected:
        target = out / 'source' / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(tar.extractfile(entries[name]).read()); hashes[name] = sha(target)
project = E.parse(out / 'source' / selected[0])
assert project.findtext('.//{*}PackageVersion') == '1.1.0'
assert project.findtext('.//{*}IsLineupPackage') == 'true'
assert project.findtext('.//{*}File/{*}TargetPath') == 'lib/netstandard1.0'
source = json.loads((out / 'source' / selected[1]).read_text())
graph_file = here / 'inputs/runtime.json'
assert sha(graph_file) == policy['original_data_sha256']['runtime.json']
graph = json.loads(graph_file.read_text())
# NuGet represents a single empty RID as an array when serializing profiles.
supports = {profile: {framework: value if isinstance(value, list) else [value] for framework, value in rows.items()}
            for profile, rows in source['supports'].items()}
assert supports == graph['supports']
assert len(graph['runtimes']) == policy['runtime_count'] == 22
assert sum(sum(len(v) for v in row.values()) for row in graph['runtimes'].values()) == policy['dependency_edges'] == 97
owners = {n.get('Include') for n in E.parse(out / 'source' / selected[2]).findall('.//{*}Package')}
owners |= {n.get('Include') for n in project.findall('.//{*}Package') + project.findall('.//{*}NativePackage')}
assert {name for row in graph['runtimes'].values() for name in row} <= owners
package = E.parse(here / 'inputs/Microsoft.NETCore.Targets.nuspec').getroot()
for element in package.iter(): element.tag = element.tag.rsplit('}', 1)[-1]
metadata = package.find('metadata'); metadata.find('authors').text += '; MSYS2 runtime metadata source port'
metadata.find('description').text += '\nOriginal dependency graph data port; implementations are supplied by the separately declared runtime packages.'
E.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/corefx', commit=policy['source_commit'])
files = E.SubElement(package, 'files')
for name, digest in policy['original_data_sha256'].items():
    path = here / 'inputs' / name; assert sha(path) == digest
    E.SubElement(files, 'file', src=path.as_posix(), target=name)
(out / '_._').write_bytes(b'')
E.SubElement(files, 'file', src=(out / '_._').as_posix(), target=policy['original_empty_marker'])
E.indent(package); E.ElementTree(package).write(out / 'Package.nuspec', encoding='utf-8', xml_declaration=True)
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', PackageId='Microsoft.NETCore.Targets', Version='1.1.0', IncludeBuildOutput='false',
    EnableDefaultItems='false', NuGetAudit='false', NuspecFile=(out / 'Package.nuspec').as_posix()).items(): E.SubElement(props, k).text = v
E.indent(tree); E.ElementTree(tree).write(out / 'Package.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'pack', str(out / 'Package.csproj'), '-c', 'Release', '--configfile',
           str(out / 'NuGet.config'), '-p:UseSharedCompilation=false', '-o', str(out / 'feed'), '-v:minimal']
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT); (out / 'pack.log').write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_commit=policy['source_commit'], source_archive_sha256=sha(archive),
    original_source_sha256=hashes, original_graph_data_sha256=sha(graph_file), source_support_profiles_verified=True,
    declared_source_lineup_owners_verified=True, runtime_rows=22, runtime_dependency_edges=97, support_profiles=14,
    command=command, exit_code=result.returncode, original_buildtools_lineup_generation_replayed=False,
    implementation_binaries=0, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS original Targets1.1 metadata:22 RIDs,97 runtime dependency edges,14 source support profiles and original marker')
