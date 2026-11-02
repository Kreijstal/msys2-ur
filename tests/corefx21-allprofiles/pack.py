"""Pack all original DLL/XML paths and unchanged published dependency groups."""
from pathlib import Path
import json
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as E

producer, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
commands = []
for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]:
    folder = out / name; folder.mkdir()
    original = E.parse(here / 'inputs' / (name.lower() + '.nuspec')).getroot()
    for element in original.iter(): element.tag = element.tag.rsplit('}', 1)[-1]
    metadata = original.find('metadata')
    for attr in ['serviceable', 'licenseUrl', 'iconUrl', 'owners']:
        node = metadata.find(attr)
        if node is not None: metadata.remove(node)
    metadata.find('authors').text += '; MSYS2 source bootstrap'
    metadata.find('description').text += '\nSource SDK8/Csc4.4 bootstrap; all original library profiles. Published XML documentation is retained as disclosed nonexecutable text data.'
    E.SubElement(metadata, 'license', type='expression').text = 'MIT'
    E.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/corefx', commit='30ab651fcb4354552bd4891619a0bdd81e0ebdbf')
    files = E.SubElement(original, 'files')
    frameworks = ['netstandard1.0', 'netstandard1.3', 'netstandard2.0'] if name.endswith('Immutable') else ['netstandard1.1', 'netstandard2.0']
    aliases = ['portable-net45%2Bwin8%2Bwp8%2Bwpa81'] if name.endswith('Immutable') else ['portable-net45%2Bwin8']
    for framework in frameworks + aliases:
        selected = frameworks[0] if framework.startswith('portable-') else framework
        dll = producer / name / selected / 'bin/Release' / (name + '.dll')
        E.SubElement(files, 'file', src=dll.as_posix(), target='lib/' + framework + '/' + name + '.dll')
        E.SubElement(files, 'file', src=(here / 'inputs/documentation' / (name + '.xml')).as_posix(), target='lib/' + framework + '/' + name + '.xml')
    for license_name in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        projection = folder / license_name
        projection.write_bytes((producer / 'source' / license_name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        E.SubElement(files, 'file', src=projection.as_posix(), target=license_name)
    (folder / 'version.txt').write_bytes(b'30ab651fcb4354552bd4891619a0bdd81e0ebdbf\r\n')
    (folder / 'useSharedDesignerContext.txt').write_bytes(b'')
    for filename in ['version.txt', 'useSharedDesignerContext.txt']:
        E.SubElement(files, 'file', src=(folder / filename).as_posix(), target=filename)
    E.indent(original); E.ElementTree(original).write(folder / 'package.nuspec', encoding='utf-8', xml_declaration=True)
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(project, 'PropertyGroup')
    for key, value in dict(TargetFramework='net8.0', IncludeBuildOutput='false', NoPackageAnalysis='false',
        GeneratePackageOnBuild='false', NuspecFile=(folder / 'package.nuspec').as_posix(), PackageId=name, Version=version,
        NuGetAudit='false', EnableDefaultItems='false', SkipValidatePackageTargetFramework='true').items(): E.SubElement(props, key).text = value
    E.indent(project); E.ElementTree(project).write(folder / 'Pack.csproj', encoding='utf-8', xml_declaration=True)
    (folder / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
    command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'pack', str(folder / 'Pack.csproj'), '-c', 'Release',
               '--configfile', str(folder / 'NuGet.config'), '-p:UseSharedCompilation=false', '-o', str(out / 'feed'),
               '-p:NuspecFile=' + str(folder / 'package.nuspec')]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (folder / 'pack.log').write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
    print('PASS packed original DLL/XML paths and dependency groups:', name, version)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, original_documentation_data=json.loads((here / 'inputs/documentation-provenance.json').read_text()),
    original_NS1x_NuGet_runtime_graph_restore_verified=False, full_dependency_goal_complete=False), indent=2) + '\n')
