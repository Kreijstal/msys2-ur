"""Build/run the source Cecil metadata port; never reads original DLL bodies."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import shutil
import xml.etree.ElementTree as E
import zipfile

producer, out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
shutil.copy2(here / 'inputs/RestoreAttributes.cs', out / 'RestoreAttributes.cs')
package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
assert hashlib.sha256(package.read_bytes()).hexdigest() == 'c32254ab0d8d040d0aed45d8b3e521c319fa035041aa029685341b46b167bb30'
with zipfile.ZipFile(package) as z: (out / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', OutputType='Exe', UseAppHost='false', AssemblyName='RestoreAttributes',
    EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true',
    CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items():
    E.SubElement(props, name).text = value
items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(out / 'RestoreAttributes.cs').as_posix())
r = E.SubElement(items, 'Reference', Include='Mono.Cecil'); E.SubElement(r, 'HintPath').text = (out / 'Mono.Cecil.dll').as_posix()
E.indent(tree); E.ElementTree(tree).write(out / 'Tool.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands = []
for label, command in [('build', [prefix / 'lib/dotnet/dotnet.exe', 'build', out / 'Tool.csproj', '-c', 'Release', '--configfile', out / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal']),
                       ('restore', [prefix / 'lib/dotnet/dotnet.exe', out / 'bin/Release/net8.0/RestoreAttributes.dll', here / 'inputs', producer, out / 'ref'])]:
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
print((out / 'restore.log').read_text())
(out / 'results.json').write_text(json.dumps(dict(commands=commands, source_metadata_projection=True,
    original_implementation_executed=False, Microsoft_private_key_signatures_reproduced=False), indent=2) + '\n')
