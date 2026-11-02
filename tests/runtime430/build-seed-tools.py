"""Build source-only metadata tools for the selected original Framework seeds."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
assert hashlib.sha256(package.read_bytes()).hexdigest() == 'c32254ab0d8d040d0aed45d8b3e521c319fa035041aa029685341b46b167bb30'
with zipfile.ZipFile(package) as z: (out / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
config = out / 'NuGet.config'; config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands = []
for name, startup, sources in [('SeedMetadata', 'SeedMetadata', ['SeedMetadata.cs']), ('Inspect', 'Program', ['Api.cs', 'Program.cs']), ('ReferenceClosure', 'ReferenceClosure', ['ReferenceClosure.cs']), ('RestoreReferenceAttributes', 'RestoreReferenceAttributes', ['RestoreReferenceAttributes.cs']), ('GenerateRuntimeFacade', 'GenerateRuntimeFacade', ['GenerateRuntimeFacade.cs']), ('PortFacadeExports', 'PortFacadeExports', ['PortFacadeExports.cs'])]:
    folder = out / name; folder.mkdir()
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(project, 'PropertyGroup')
    for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName=name, StartupObject=startup, UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true', CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items(): E.SubElement(pg, n).text = v
    items = E.SubElement(project, 'ItemGroup')
    for source in sources: E.SubElement(items, 'Compile', Include=(here / 'inputs' / source).as_posix())
    E.SubElement(items, 'Reference', Include='Mono.Cecil', HintPath=(out / 'Mono.Cecil.dll').as_posix())
    E.indent(project); E.ElementTree(project).write(folder / (name + '.csproj'), encoding='utf-8', xml_declaration=True)
    command = [str(prefix / 'lib/dotnet/dotnet.exe'), 'build', str(folder / (name + '.csproj')), '-c', 'Release', '--configfile', str(config), '-p:UseSharedCompilation=false', '-v:minimal']
    env = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '-build.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')[-5000:]
(out / 'results.json').write_text(json.dumps(dict(commands=commands, Cecil_source_archive_sha256=hashlib.sha256(package.read_bytes()).hexdigest(), original_binaries_executed=False), indent=2) + '\n')
print('PASS source Framework seed metadata tools built with warnings as errors')
