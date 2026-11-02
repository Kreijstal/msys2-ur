"""Fresh package consumers, exact archive bytes, and legacy restore inventory."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed, out, prefix, compiler, host = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
config = E.Element('configuration'); sources = E.SubElement(config, 'packageSources'); E.SubElement(sources, 'clear')
E.SubElement(sources, 'add', key='candidate', value=feed.as_posix())
installed_feed = (prefix / 'lib/dotnet/library-packs').resolve()
same_feed = feed.as_posix().casefold() == installed_feed.as_posix().casefold()
if not same_feed:
    E.SubElement(sources, 'add', key='installed', value=installed_feed.as_posix())
mapping = E.SubElement(config, 'packageSourceMapping')
candidate = E.SubElement(mapping, 'packageSource', key='candidate')
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']: E.SubElement(candidate, 'package', pattern=name)
if same_feed:
    E.SubElement(candidate, 'package', pattern='*')
else:
    E.SubElement(E.SubElement(mapping, 'packageSource', key='installed'), 'package', pattern='*')
E.indent(config); E.ElementTree(config).write(out / 'NuGet.config', encoding='utf-8', xml_declaration=True)
environment = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
def run(label, command, required=True):
    result = subprocess.run([str(p) for p in command], env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout)
    commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    if required: assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
    return result
def project(directory, framework):
    directory.mkdir(); tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
    for name, value in dict(TargetFramework=framework, AssemblyName='Bridge', EnableDefaultItems='false', EnableNETAnalyzers='false',
        NuGetAudit='false', TreatWarningsAsErrors='true', LangVersion='7.3', DefineConstants='HAS_ITEMREF',
        CscToolPath=compiler.as_posix(), CscToolExe='csc44.cmd', UseSharedCompilation='false').items(): E.SubElement(props, name).text = value
    items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(here / 'inputs/Bridge.cs').as_posix())
    for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]: E.SubElement(items, 'PackageReference', Include=name, Version='[' + version + ']')
    E.indent(tree); E.ElementTree(tree).write(directory / 'Bridge.csproj', encoding='utf-8', xml_declaration=True)
    return directory / 'Bridge.csproj'
consumer = project(out / 'standard2', 'netstandard2.0')
run('standard2-build', [dotnet, 'build', consumer, '-c', 'Release', '--configfile', out / 'NuGet.config', '-v:minimal'])
owned = out / 'owned'; owned.mkdir(); shutil.copy2(out / 'standard2/bin/Release/netstandard2.0/Bridge.dll', owned / 'Bridge.dll')
archives = {}
for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]:
    package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == name.lower() + '.' + version + '.nupkg')
    cached = out / 'cache' / name.lower() / version / (name.lower() + '.' + version + '.nupkg')
    assert cached.read_bytes() == package.read_bytes()
    with zipfile.ZipFile(package) as z: (owned / (name + '.dll')).write_bytes(z.read('lib/netstandard2.0/' + name + '.dll'))
    archives[name] = hashlib.sha256(package.read_bytes()).hexdigest()
assets = json.loads((out / 'standard2/obj/project.assets.json').read_text())
for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]:
    rows = [target[name + '/' + version] for target in assets['targets'].values() if name + '/' + version in target]
    assert rows and all(list(row['compile']) == ['lib/netstandard2.0/' + name + '.dll'] for row in rows)
run('standard2-run', [dotnet, host, owned])
legacy = project(out / 'legacy13', 'netstandard1.3')
result = run('legacy13-restore', [dotnet, 'restore', legacy, '--configfile', out / 'NuGet.config', '-v:minimal'], required=False)
legacy_assets = out / 'legacy13/obj/project.assets.json'
diagnostics = json.loads(legacy_assets.read_text()).get('logs', []) if legacy_assets.exists() else []
(out / 'results.json').write_text(json.dumps(dict(commands=commands, fresh_NS2_exact_source_archives=archives,
    fresh_NS2_compile_and_isolated_runtime_passed=True, original_NS13_restore_exit_code=result.returncode,
    original_NS13_restore_diagnostics=diagnostics, historical_runtimes_executed=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS fresh NS2 exact archive/cache bytes, original compile selection and isolated source implementations')
print('Original NS1.3 restore exit:', result.returncode, '; diagnostic codes:', sorted({r.get('code') for r in diagnostics}))
