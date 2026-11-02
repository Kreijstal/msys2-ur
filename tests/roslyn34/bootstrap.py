"""Create a local-only original Csc driver from seed libraries.

The three original CLI inputs are unchanged. The small entry/ALC wrappers are
explicit bootstrap ports to NET8, not the original Toolset executables.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive, seed, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists()
out.mkdir()
here = Path(__file__).parent
for name in ['CompilerEntry.cs', 'Driver.cs']:
    shutil.copy2(here / 'inputs' / name, out / name)
key = here / 'inputs/MicrosoftShared.pubkey.hex'
(out / 'Roslyn.public.snk').write_bytes(bytes.fromhex(key.read_text()))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '8bf783851ac159bf7f3d5e1388ce98549352676a80a49eb681e85bcbf6bdc601'
selected = ['src/Compilers/Shared/Csc.cs', 'src/Compilers/Core/CommandLine/ConsoleUtil.cs',
            'src/Compilers/Shared/CoreClrAnalyzerAssemblyLoader.cs']
with tarfile.open(archive) as t:
    assert t.pax_headers['comment'] == '82f2e2541478e239dc4b04f231e90dc2b3dcb422'
    entries = {m.name.partition('/')[2]: m for m in t if m.isfile()}
    for n in selected:
        dest = out / 'original' / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(t.extractfile(entries[n]).read())

def project(folder, name, exe, version):
    folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    values = dict(TargetFramework='net8.0', AssemblyName=name, OutputType='Exe' if exe else 'Library',
                  EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false',
                  UseAppHost='false', TreatWarningsAsErrors='true', Nullable='enable' if exe else 'disable',
                  LangVersion='preview' if exe else '8.0', DefineConstants='TRACE;NETCOREAPP2_1',
                  CscToolPath=((prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap') if version == 5 else compiler).as_posix(),
                  CscToolExe='csc50.cmd' if version == 5 else 'csc44.cmd')
    if not exe:
        values.update(SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile='../Roslyn.public.snk')
    for n, v in values.items(): E.SubElement(pg, n).text = v
    return tree, E.SubElement(tree, 'ItemGroup')

tree, items = project(out / 'entry', 'csc', False, 5)
for p in selected:
    E.SubElement(items, 'Compile', Include=(out / 'original' / p).as_posix())
E.SubElement(items, 'Compile', Include=(out / 'CompilerEntry.cs').as_posix())
for n in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']:
    r = E.SubElement(items, 'Reference', Include=n)
    E.SubElement(r, 'HintPath').text = (seed / n / 'bin/Release/netstandard2.0' / (n + '.dll')).as_posix()
    E.SubElement(r, 'Private').text = 'false'
E.indent(tree); E.ElementTree(tree).write(out / 'entry/Build.csproj', encoding='utf-8', xml_declaration=True)
tree, items = project(out / 'driver', 'Driver', True, 5)
tree.find('.//CscToolPath').text = (prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix()
E.SubElement(items, 'Compile', Include=(out / 'Driver.cs').as_posix())
E.indent(tree); E.ElementTree(tree).write(out / 'driver/Build.csproj', encoding='utf-8', xml_declaration=True)
runtime = out / 'runtime'; runtime.mkdir()
for n in ['Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp']:
    p = seed / n / 'bin/Release/netstandard2.0' / (n + '.dll')
    shutil.copy2(p, runtime / p.name)
supports = json.loads((seed / 'source-inputs.json').read_text())['support']
for name, record in supports.items():
    p = prefix / 'lib/dotnet/library-packs' / (name.lower() + '.' + record['version'] + '.nupkg')
    assert sha(p) == record['archive_sha256']
    with zipfile.ZipFile(p) as z:
        member = 'lib/netstandard2.0/' + name + '.dll'
        if name == 'System.Text.Encoding.CodePages':
            member = 'runtimes/win/lib/netcoreapp2.0/' + name + '.dll'
        (runtime / (name + '.dll')).write_bytes(z.read(member))
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
driver = out / 'driver/bin/Release/net8.0/Driver.dll'
dotnet = prefix / 'lib/dotnet/dotnet.exe'
(out / 'csc34.cmd').write_bytes(('@echo off\r\nset "ROSLYN34_COMPILER_DIRECTORY=' + runtime.as_posix() + '"\r\n"' + dotnet.as_posix() + '" "' + driver.as_posix() + '" %*\r\nexit /b %errorlevel%\r\n').encode())
(out / 'bootstrap-inputs.json').write_text(json.dumps(dict(original_cli_inputs={p: sha(out / 'original' / p) for p in selected},
    bootstrap_ports={n: sha(here / 'inputs' / n) for n in ['CompilerEntry.cs', 'Driver.cs']},
    original_cli_cs_changes=0, original_Toolset_executables_reproduced=False, original_NETCore21_runtime_executed=False), indent=2) + '\n')
print('PASS prepared isolated original Roslyn3.4 local Csc bootstrap')
