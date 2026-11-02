"""Pack the original references, data assets, aliases and framework markers."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E

producer, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
policies = json.loads((here / 'inputs/published-package-policy.json').read_text())
commands = []
for name, policy in policies.items():
    folder = out / name; folder.mkdir()
    package = E.parse(here / 'inputs' / name / 'original.nuspec').getroot()
    for element in package.iter(): element.tag = element.tag.rsplit('}', 1)[-1]
    metadata = package.find('metadata'); metadata.find('authors').text += '; MSYS2 source reference port'
    metadata.find('description').text += '\nOriginal reference profile, enum implementation and complete NET46 facade, built from source. Original assembly versions and dependency scopes preserved.'
    E.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/source-build-reference-packages', commit=policy['source_reference_package_commit'])
    files = E.SubElement(package, 'files')
    for path in policy['reference_DLL_sha256']:
        framework = path.split('/')[1]
        if framework == 'netcore50':
            digest = policy['reference_DLL_sha256'][path]
            aliases = [p.split('/')[1] for p,h in policy['reference_DLL_sha256'].items() if h == digest and '/netcore50/' not in p]
            assert len(aliases) == 1, (name, aliases)
            framework = aliases[0]
        dll = producer / path
        assert dll.is_file(); E.SubElement(files, 'file', src=dll.as_posix(), target=path)
    for path, digest in policy['original_data_sha256'].items():
        source = here / 'inputs' / name / 'data' / path
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
        E.SubElement(files, 'file', src=source.as_posix(), target=path)
    E.indent(package); E.ElementTree(package).write(folder / 'Package.nuspec', encoding='utf-8', xml_declaration=True)
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(project, 'PropertyGroup')
    for key, value in dict(TargetFramework='net8.0', PackageId=name, Version='4.3.0', IncludeBuildOutput='false',
        EnableDefaultItems='false', NuGetAudit='false', NuspecFile=(folder / 'Package.nuspec').as_posix()).items(): E.SubElement(props, key).text = value
    E.indent(project); E.ElementTree(project).write(folder / 'Package.csproj', encoding='utf-8', xml_declaration=True)
    (folder / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
    command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'pack', str(folder / 'Package.csproj'), '-c', 'Release', '--configfile', str(folder / 'NuGet.config'),
               '-p:UseSharedCompilation=false', '-o', str(out / 'feed'), '-v:minimal']
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (folder / 'pack.log').write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
    print('PASS packed original reference/data/marker paths:', name)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, source_Framework_owned_implementations_included=True, runtime_any_or_AOT_providers_included=False,
    original_dependency_groups_preserved=True, full_dependency_goal_complete=False), indent=2) + '\n')
