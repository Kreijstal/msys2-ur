"""Rebuild the frozen metadata inspector using installed source Cecil 0.11."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists()
out.mkdir()
here = Path(__file__).parent
package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
with zipfile.ZipFile(package) as z:
    (out / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='Inspect', UseAppHost='false',
    EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable',
    TreatWarningsAsErrors='true', CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(),
    CscToolExe='csc50.cmd').items(): E.SubElement(pg, name).text = value
items = E.SubElement(tree, 'ItemGroup')
for name in ['Api.cs', 'Program.cs']:
    E.SubElement(items, 'Compile', Include=(here / 'metadata-inputs' / name).as_posix())
reference = E.SubElement(items, 'Reference', Include='Mono.Cecil')
E.SubElement(reference, 'HintPath').text = (out / 'Mono.Cecil.dll').as_posix()
E.indent(tree); E.ElementTree(tree).write(out / 'Inspect.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'build', str(out / 'Inspect.csproj'), '-c', 'Release',
           '--configfile', str(out / 'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal']
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'build.log').write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
(out / 'tool-inputs.json').write_text(json.dumps(dict(command=command, exit_code=result.returncode,
    source_files={n: hashlib.sha256((here / 'metadata-inputs' / n).read_bytes()).hexdigest() for n in ['Api.cs', 'Program.cs']},
    Cecil_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
    Cecil_DLL_sha256=hashlib.sha256((out / 'Mono.Cecil.dll').read_bytes()).hexdigest()), indent=2) + '\n')
print('PASS source metadata inspector rebuilt with source Cecil0.11, warnings as errors')
