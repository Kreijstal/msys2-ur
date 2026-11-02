"""Read original/candidate PE resources without executing original assemblies."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

archives, prepared, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists()
out.mkdir()
here = Path(__file__).parent
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='ReadResources',
    UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false',
    TreatWarningsAsErrors='true', CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),
    CscToolExe='csc50.cmd').items(): E.SubElement(pg, name).text = value
E.SubElement(E.SubElement(tree, 'ItemGroup'), 'Compile', Include=(here / 'inputs/ReadResources.cs').as_posix())
E.indent(tree); E.ElementTree(tree).write(out / 'ReadResources.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
dotnet = prefix / 'lib/dotnet/dotnet.exe'
commands = []
def run(name, command):
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '.log')).write_bytes(result.stdout)
    commands.append(dict(name=name, command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
    return result.stdout
run('build', [dotnet, 'build', out / 'ReadResources.csproj', '-c', 'Release', '--configfile', out / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
tool = out / 'bin/Release/net8.0/ReadResources.dll'
results = {}
for ident, name, expected_sha in [
    ('common', 'Microsoft.CodeAnalysis', '5cd71d8b94e620e046e6d342a2d6fec6bc615c2b17967fc7e4ccc74de833368b'),
    ('csharp', 'Microsoft.CodeAnalysis.CSharp', '3e4515e48668daf946af4b31d9a6cffddcb3ed2466f6f818577d95a438a31e66')]:
    package = archives / ('microsoft.codeanalysis.' + ident + '.3.4.0.metadata-only.nupkg')
    assert hashlib.sha256(package.read_bytes()).hexdigest() == expected_sha
    original = out / 'metadata-only' / ident; original.mkdir(parents=True)
    candidate = prepared / name / 'bin/Release/netstandard2.0'
    paths = []
    with zipfile.ZipFile(package) as z:
        for member in z.namelist():
            if member.startswith('lib/netstandard2.0/') and member.endswith('.dll'):
                relative = member.removeprefix('lib/netstandard2.0/')
                dest = original / relative; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(member)); paths.append(relative)
        xml_before = z.read('lib/netstandard2.0/' + name + '.xml')
        xml_after = (candidate / (name + '.xml')).read_bytes()
        # XML parsers perform the specified XML newline handling. Preserve all
        # member identifiers and text, and separately record byte equality.
        assert E.tostring(E.fromstring(xml_before)) == E.tostring(E.fromstring(xml_after)), (name, 'XML documentation')
        assert (candidate / (name + '.pdb')).read_bytes()[:4] == b'BSJB'
    before = json.loads(run(ident + '-original', [dotnet, tool, *[original / p for p in paths]]))
    after = json.loads(run(ident + '-candidate', [dotnet, tool, *[candidate / p for p in paths]]))
    assert len(before) == len(after) == 14
    total = 0
    for path, want, got in zip(paths, before, after):
        for key in ['name', 'version', 'public_key', 'public_key_token', 'attributes', 'resources', 'embedded_nonresource_blob_hashes', 'exported_types', 'references', 'native_version']:
            assert got[key] == want[key], (path, key, 'published', want[key] if key != 'resources' else 'values', 'candidate', got[key] if key != 'resources' else 'values')
        total += sum(len(v) for v in got['resources'].values())
    results[name] = dict(assemblies=14, localized_satellites=13, resource_strings=total,
        XML_documentation_bytes_identical=xml_before == xml_after,
        XML_documentation_sha256=hashlib.sha256(xml_after).hexdigest(), source_portable_PDB_present=True)
    print('PASS', name, 'neutral + 13 original localized satellites;', total, 'exact resource strings and original metadata')
(out / 'results.json').write_text(json.dumps(dict(libraries=results, commands=commands,
    original_assemblies_executed=False, inspector_source_sha256=hashlib.sha256((here / 'inputs/ReadResources.cs').read_bytes()).hexdigest()), indent=2) + '\n')
