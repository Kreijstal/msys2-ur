"""Build the original dependency-only metapackage from pinned source/data."""
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
provenance = json.loads((here / 'inputs/provenance.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == provenance['source_archive_sha256']
selected = ['pkg/NETStandard.Library/NETStandard.Library.pkgproj',
            'pkg/NETStandard.Library/NETStandard.Library.packages.targets', 'LICENSE', 'THIRD-PARTY-NOTICES']
source = out / 'source'; hashes = {}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == provenance['source_commit']
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name in selected:
        p = source / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(tar.extractfile(entries[name]).read()); hashes[name] = sha(p)
assert E.parse(source / selected[0]).findtext('.//{*}PackageVersion') == '1.6.1'
declared = {p.get('Include') for p in E.parse(source / selected[1]).findall('.//{*}Package')}
groups = provenance['dependency_groups']
assert len(groups) == 4 and [len(g['dependencies']) for g in groups] == [23, 30, 31, 44]
assert {d['id'] for g in groups for d in g['dependencies']} == declared | {'Microsoft.NETCore.Platforms'}
assert all(d['version'] == ('1.1.0' if d['id'] == 'Microsoft.NETCore.Platforms' else '4.3.0') for g in groups for d in g['dependencies'])
package = E.parse(here / 'inputs/NETStandard.Library.nuspec').getroot()
for element in package.iter(): element.tag = element.tag.rsplit('}', 1)[-1]
metadata = package.find('metadata')
metadata.find('authors').text += '; MSYS2 dependency metadata source port'
metadata.find('description').text += '\nDependency-only source metadata port; no runtime or reference implementations are included.'
E.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/corefx', commit=provenance['source_commit'])
files = E.SubElement(package, 'files')
for name, digest in provenance['original_nonmetadata_files'].items():
    original = here / 'inputs' / name; assert sha(original) == digest
    E.SubElement(files, 'file', src=original.as_posix(), target=name)
E.indent(package); E.ElementTree(package).write(out / 'Package.nuspec', encoding='utf-8', xml_declaration=True)
project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(project, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', PackageId='NETStandard.Library', Version='1.6.1', IncludeBuildOutput='false',
    EnableDefaultItems='false', NuGetAudit='false', NuspecFile=(out / 'Package.nuspec').as_posix()).items(): E.SubElement(props, k).text = v
E.indent(project); E.ElementTree(project).write(out / 'Package.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'pack', str(out / 'Package.csproj'), '-c', 'Release',
           '--configfile', str(out / 'NuGet.config'), '-p:UseSharedCompilation=false', '-o', str(out / 'feed'), '-v:minimal']
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'pack.log').write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_commit=provenance['source_commit'], source_archive_sha256=sha(archive),
    original_source_files=hashes, dependency_groups=groups, original_license_data=provenance['original_nonmetadata_files'],
    command=command, exit_code=result.returncode, implementation_binaries=0, original_buildtools_replayed=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS source NETStandard.Library1.6.1: four original dependency groups, 128 dependency edges; no implementation binaries')
