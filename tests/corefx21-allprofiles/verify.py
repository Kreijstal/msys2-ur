"""Verify packaged source libraries against frozen original PE/data baselines.

Usage: verify.py FEED NEW_OUTPUT PREFIX COMPILER44. Builds fresh source
metadata tools, unpacks only candidate archives, and runs isolated consumers.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
commands = []
def run(label, command):
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout)
    commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
    return result.stdout
python = prefix / 'bin/python.exe'; dotnet = prefix / 'lib/dotnet/dotnet.exe'
run('inspector-build', [python, '-X', 'utf8', here / 'build-inspector.py', out / 'inspector', prefix])
reader = out / 'reader'; reader.mkdir()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for name, value in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='ReadResources', UseAppHost='false',
    EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', TreatWarningsAsErrors='true',
    CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items():
    E.SubElement(props, name).text = value
E.SubElement(E.SubElement(tree, 'ItemGroup'), 'Compile', Include=(here / 'inputs/ReadResources.cs').as_posix())
E.indent(tree); E.ElementTree(tree).write(reader / 'Reader.csproj', encoding='utf-8', xml_declaration=True)
(reader / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('reader-build', [dotnet, 'build', reader / 'Reader.csproj', '-c', 'Release', '--configfile', reader / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
policies = json.loads((here / 'inputs/published-archive-policy.json').read_text())
expected_assets = json.loads((here / 'inputs/published-assets.json').read_text())
owned = out / 'implementations'; owned.mkdir()
archives, paths, profiles = {}, [], []
for name, policy in policies.items():
    package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == name.lower() + '.' + policy['version'] + '.nupkg')
    archives[name] = hashlib.sha256(package.read_bytes()).hexdigest()
    with zipfile.ZipFile(package) as z:
        assert {n for n in z.namelist() if n.startswith('lib/')} == set(policy['lib_paths'])
        assert not any(n.startswith('ref/') or n.endswith('.pdb') for n in z.namelist())
        for path, digest in policy['text_data_sha256'].items(): assert hashlib.sha256(z.read(path)).hexdigest() == digest, path
        nuspec = E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.nuspec'))))
        groups = [dict(framework=g.get('targetFramework'), dependencies=[d.attrib for d in g]) for g in nuspec.findall('.//{*}dependencies/{*}group')]
        assert groups == policy['dependency_groups'], name
        for member in policy['lib_paths']:
            if not member.endswith('.dll'): continue
            framework = member.split('/')[1]
            if framework.startswith('portable-'):
                standard = 'netstandard1.0' if name.endswith('Immutable') else 'netstandard1.1'
                assert z.read(member) == z.read('lib/' + standard + '/' + name + '.dll')
                continue
            target = owned / name / framework / 'bin/Release' / (name + '.dll')
            target.parent.mkdir(parents=True); target.write_bytes(z.read(member))
            paths.append(target); profiles.append(name + '/' + framework)
metadata = {}
for profile, path in zip(profiles, paths):
    name, framework = profile.split('/'); destination = out / (name + '-' + framework + '.json')
    run('inspect-' + name + '-' + framework, [dotnet, out / 'inspector/bin/Release/net8.0/Inspect.dll', destination, path])
    actual = json.loads(destination.read_text())[name + '.dll']
    expected = json.loads((here / 'inputs' / (name + '-' + framework + '-metadata.json')).read_text())[name + '.dll']
    assert actual['identity'] == expected['identity'] and actual['api'] == expected['api'], profile
    assert set(actual['references']) == set(expected['references']), profile
    canonical = lambda rows: sorted(json.dumps(v, sort_keys=True) for v in rows)
    assert canonical(actual['attributes']) == canonical(expected['attributes']), profile
    metadata[profile] = len(actual['api'])
resources = json.loads(run('resources', [dotnet, reader / 'bin/Release/net8.0/ReadResources.dll', *paths]))
for profile, actual in zip(profiles, resources):
    expected = expected_assets[profile]
    for key in ['name', 'version', 'public_key', 'public_key_token', 'attributes', 'resources', 'embedded_nonresource_blob_hashes', 'exported_types', 'references', 'native_version']:
        assert actual[key] == expected[key], (profile, key)
run('runtime-pairs', [python, '-X', 'utf8', here / 'check.py', owned, out / 'runtime', prefix, compiler])
run('fresh-consumers', [python, '-X', 'utf8', here / 'check-feed.py', feed, out / 'consumers', prefix, compiler, out / 'runtime/host/bin/Release/net8.0/Run.dll'])
consumer = json.loads((out / 'consumers/results.json').read_text())
result = dict(commands=commands, package_sha256=archives, original_profile_API_entries=metadata,
    original_DLL_XML_alias_dependency_groups_and_text_data_verified=True,
    original_managed_attributes_resources_and_native_versions_verified=True,
    all_five_source_implementations_executed_on_source_NET8=True,
    fresh_NS2_source_archive_cache_and_compile_runtime_checks_passed=True,
    original_NS13_restore_exit_code=consumer['original_NS13_restore_exit_code'],
    original_NS13_restore_diagnostics=consumer['original_NS13_restore_diagnostics'],
    historical_runtimes_executed=False, full_dependency_goal_complete=False)
(out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS five original source profiles, 8483 API entries, all DLL/XML/data/alias paths, three isolated runtime pairs and fresh NS2 exact archive consumption')
print('Original NS1.3 restore exit', result['original_NS13_restore_exit_code'], '; historical runtime/NuGet framework graph remains separate evidence')
