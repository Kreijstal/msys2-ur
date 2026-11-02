"""Execute all five candidate implementations in three exact-version pairs."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

producer, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
config = out / 'NuGet.config'; config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands = []
def run(label, command):
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout)
    commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
    return result.stdout

def project(folder, host=False):
    folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
    values = dict(TargetFramework='net8.0' if host else 'netstandard2.0', AssemblyName='Run' if host else 'Bridge',
        OutputType='Exe' if host else 'Library', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false',
        NuGetAudit='false', TreatWarningsAsErrors='true', Nullable='enable' if host else 'disable',
        LangVersion='preview' if host else '7.3', UseSharedCompilation='false',
        CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix() if host else compiler.as_posix(),
        CscToolExe='csc50.cmd' if host else 'csc44.cmd')
    if not host: values.update(DisableImplicitFrameworkReferences='true', NoStdLib='true')
    for n, v in values.items(): E.SubElement(pg, n).text = v
    return tree, pg, E.SubElement(tree, 'ItemGroup')

tree, pg, items = project(out / 'host', True)
E.SubElement(items, 'Compile', Include=(here / 'inputs/Run.cs').as_posix())
E.indent(tree); E.ElementTree(tree).write(out / 'host/Run.csproj', encoding='utf-8', xml_declaration=True)
dotnet = prefix / 'lib/dotnet/dotnet.exe'
run('host-build', [dotnet, 'build', out / 'host/Run.csproj', '-c', 'Release', '--configfile', config, '-v:minimal'])
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll')); assert len(refs) == 113
pairs = [('legacy10', 'netstandard1.0', 'netstandard1.1'), ('legacy13', 'netstandard1.3', 'netstandard1.1'), ('standard2', 'netstandard2.0', 'netstandard2.0')]
results = {}
for label, imm, meta in pairs:
    folder = out / label; tree, pg, items = project(folder)
    if imm != 'netstandard1.0': E.SubElement(pg, 'DefineConstants').text = 'HAS_ITEMREF'
    E.SubElement(items, 'Compile', Include=(here / 'inputs/Bridge.cs').as_posix())
    candidates = [producer / 'System.Collections.Immutable' / imm / 'bin/Release/System.Collections.Immutable.dll',
                  producer / 'System.Reflection.Metadata' / meta / 'bin/Release/System.Reflection.Metadata.dll']
    for p in refs + candidates: E.SubElement(items, 'Reference', Include=p.stem, HintPath=p.as_posix(), Private='false')
    E.indent(tree); E.ElementTree(tree).write(folder / 'Bridge.csproj', encoding='utf-8', xml_declaration=True)
    run(label + '-build', [dotnet, 'build', folder / 'Bridge.csproj', '-c', 'Release', '--configfile', config, '-v:minimal'])
    owned = folder / 'owned'; owned.mkdir()
    shutil.copy2(folder / 'bin/Release/netstandard2.0/Bridge.dll', owned / 'Bridge.dll')
    for p in candidates: shutil.copy2(p, owned / p.name)
    log = run(label + '-run', [dotnet, out / 'host/bin/Release/net8.0/Run.dll', owned])
    results[label] = dict(Immutable_profile=imm, Metadata_profile=meta,
        executed_source_DLL_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in candidates})
    print(log.decode('utf-8', errors='replace'))
(out / 'results.json').write_text(json.dumps(dict(commands=commands, profiles=results,
    all_five_source_implementations_executed=True, runtime='installed source NET8', historical_runtimes_executed=False,
    original_NS1x_NuGet_dependency_restore_verified=False), indent=2) + '\n')
