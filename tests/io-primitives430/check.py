"""Validate all original reference assets, NuGet semantics and compile consumers."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

feed, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
policies = json.loads((here / 'inputs/published-package-policy.json').read_text())
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
commands = []
environment = dict(os.environ, DOTNET_CLI_HOME=(out / 'cli-home').as_posix(), NUGET_PACKAGES=(out / 'cache').as_posix(), MSBuildEnableWorkloadResolver='false')
def run(label, command, required=True):
    command = [str(p) for p in command]
    result = subprocess.run(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    if required: assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-4000:])
    return result

dotnet = prefix / 'lib/dotnet/dotnet.exe'
run('inspector-build', [sys.executable, here / 'build-inspector.py', out / 'inspector', prefix])
run('forwarder-inspector-build', [sys.executable, here / 'build-forwarder-inspector.py', out / 'forwarder-inspector', prefix])
tool = out / 'semantics'; tool.mkdir()
project = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(project, 'PropertyGroup')
for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='Check', UseAppHost='false', EnableDefaultItems='false',
    EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true',
    CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items(): E.SubElement(pg, n).text = v
items = E.SubElement(project, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(here / 'inputs/Check.cs').as_posix())
sdk = prefix / 'lib/dotnet/sdk/8.0.131'
for n in ['NuGet.Packaging', 'NuGet.Frameworks', 'NuGet.Versioning', 'NuGet.Common']:
    E.SubElement(items, 'Reference', Include=n, HintPath=(sdk / (n + '.dll')).as_posix())
E.indent(project); E.ElementTree(project).write(tool / 'Check.csproj', encoding='utf-8', xml_declaration=True)
config = out / 'NuGet.config'; config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('semantics-build', [dotnet, 'build', tool / 'Check.csproj', '-c', 'Release', '--configfile', config, '-p:UseSharedCompilation=false', '-v:minimal'])
resource_tool = out / 'resources'; resource_tool.mkdir()
resource_project = E.fromstring(E.tostring(project))
resource_project.find('PropertyGroup/AssemblyName').text = 'ReadResources'
resource_items = resource_project.find('ItemGroup'); resource_items.clear()
E.SubElement(resource_items, 'Compile', Include=(here / 'inputs/ReadResources.cs').as_posix())
# The original standalone PE reader predates nullable annotations.
resource_project.find('PropertyGroup/Nullable').text = 'disable'
E.indent(resource_project); E.ElementTree(resource_project).write(resource_tool / 'ReadResources.csproj', encoding='utf-8', xml_declaration=True)
run('resources-build', [dotnet, 'build', resource_tool / 'ReadResources.csproj', '-c', 'Release', '--configfile', config, '-p:UseSharedCompilation=false', '-v:minimal'])
resource_baselines = json.loads((here / 'inputs/reference-data.json').read_text())
archives, contracts, restores = {}, {}, {}
for name, policy in policies.items():
    package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == (name + '.4.3.0.nupkg').lower())
    folder = out / name; folder.mkdir()
    with zipfile.ZipFile(package) as z:
        expected = set(policy['reference_DLL_sha256']) | set(policy['original_data_sha256'])
        actual = {n for n in z.namelist() if n.startswith(('ref/', 'lib/')) or n in policy['original_data_sha256']}
        assert actual == expected, (actual - expected, expected - actual)
        assert {n for n in z.namelist() if n.endswith('.dll')} == set(policy['reference_DLL_sha256'])
        assert len([n for n in actual if n.endswith('_._')]) == 22
        assert {n for n in z.namelist() if n.startswith('lib/') and n.endswith('.dll')} == ({'lib/net462/System.IO.dll'} if name == 'System.IO' else set())
        if name == 'System.IO': assert z.read('lib/net462/System.IO.dll') == z.read('ref/net462/System.IO.dll')
        assert not any(n.endswith('.exe') for n in z.namelist())
        for n, digest in policy['original_data_sha256'].items(): assert hashlib.sha256(z.read(n)).hexdigest() == digest, n
        alias = 'netstandard1.0' if name == 'System.Reflection.Primitives' else 'netstandard1.3'
        assert z.read('ref/netcore50/' + name + '.dll') == z.read('ref/' + alias + '/' + name + '.dll')
        for asset in policy['reference_DLL_sha256']:
            if '/netcore50/' in asset or asset.startswith('lib/'): continue
            tfm = asset.split('/')[1]; profile = name + '-' + tfm
            target = folder / tfm; target.mkdir(); dll = target / (name + '.dll'); dll.write_bytes(z.read(asset))
            baseline = json.loads((here / 'inputs' / (profile + '.json')).read_text())[name + '.dll']
            run(profile + '-inspect', [dotnet, out / 'inspector/bin/Release/net8.0/Inspect.dll', target / 'metadata.json', dll])
            got = json.loads((target / 'metadata.json').read_text())[name + '.dll']
            assert got['identity'] == baseline['identity'] and got['api'] == baseline['api'], profile
            assert set(got['references']) == set(baseline['references']), profile
            canonical = lambda a: sorted(json.dumps(v, sort_keys=True) for v in a)
            assert canonical(got['attributes']) == canonical(baseline['attributes']), profile
            assert any(a['type'] == 'System.Runtime.CompilerServices.ReferenceAssemblyAttribute' for a in got['attributes']) == (tfm != 'net462')
            run(profile + '-forwarders', [dotnet, out / 'forwarder-inspector/bin/Release/net8.0/Forwarders.dll', target / 'forwarders.json', dll])
            exports = json.loads((target / 'forwarders.json').read_text())[0]
            original_exports = json.loads((here / 'inputs/baseline1' / (profile + '-forwarders.json')).read_text())[0]
            for field in ['identity', 'reference_only', 'assembly_references', 'exported_types']: assert exports[field] == original_exports[field], (profile, field)
            resource_result = run(profile + '-resources', [dotnet, resource_tool / 'bin/Release/net8.0/ReadResources.dll', dll])
            resource_actual = json.loads(resource_result.stdout)[0]
            resource_expected = next(r for r in resource_baselines if r['name'] == name and '/' + tfm + '/' in r['file'])
            for field in ['name', 'version', 'public_key', 'public_key_token', 'attributes', 'resources', 'embedded_nonresource_blob_hashes', 'exported_types', 'native_version', 'references']:
                assert resource_actual[field] == resource_expected[field], (profile, field)
            closure = set()
            def select(ident):
                if ident in closure: return
                closure.add(ident)
                for ref in matrix[ident]['references']:
                    n, version = ref.split(', Version='); select(n + '/' + version.split(',')[0])
            if tfm != 'net462':
                for ref in got['references']:
                    n, version = ref.split(', Version='); select(n + '/' + version.split(',')[0])
            selected_refs = {}
            for ident in sorted(closure):
                depname, version = ident.split('/')
                if depname not in selected_refs or tuple(map(int, version.split('.'))) > tuple(map(int, selected_refs[depname].split('/')[1].split('.'))): selected_refs[depname] = ident
            refs = [prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / ident / (ident.split('/')[0] + '.dll') for ident in sorted(selected_refs.values())]
            args = ['/nostdlib+', '/target:library', '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/out:"' + (target / 'Probe.dll').as_posix() + '"']
            if tfm == 'net462': refs = [prefix / 'lib/dotnet/reference-packs/netframework46-contracts-bootstrap/ref/mscorlib.dll']
            if name == 'System.Reflection.Primitives': args.append('/define:PRIMITIVES')
            elif tfm in ['netstandard1.5', 'net462']: args.append('/define:IO15')
            args += ['/reference:"' + p.as_posix() + '"' for p in refs + [dll]] + ['"' + (here / 'inputs/Probe.cs').as_posix() + '"']
            rsp = target / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
            run(profile + '-compile', [dotnet, compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
            contracts[profile] = dict(API_entries=len(got['api']), identity=got['identity'], reference_assembly_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(), compile_consumer_passed=True, original_native_versions_and_resources_verified=True)
            print('PASS original reference identity/API/attributes/references and compile consumer:', profile, len(got['api']), flush=True)
    run(name + '-semantics', [dotnet, tool / 'bin/Release/net8.0/Check.dll', package, here / 'inputs/published-package-policy.json'])
    archives[name] = dict(sha256=hashlib.sha256(package.read_bytes()).hexdigest(), markers=22, original_data_and_reference_paths_verified=True, original_dependencies_and_framework_selection_verified=True)
    print('PASS original aliases, 22 markers, documentation, licenses and NuGet semantics:', name, flush=True)

facade = out / 'System.IO/net462/System.IO.dll'
run('facade-forwarders', [dotnet, out / 'forwarder-inspector/bin/Release/net8.0/Forwarders.dll', out / 'facade-forwarders.json', facade])
got = json.loads((out / 'facade-forwarders.json').read_text())[0]
expected = json.loads((here / 'inputs/net462-exported-types.json').read_text())
for field in ['identity', 'reference_only', 'assembly_references', 'exported_types']:
    assert got[field] == expected[field], field
host = out / 'facade-host'; host.mkdir()
host_project = E.fromstring(E.tostring(project)); host_project.find('PropertyGroup/AssemblyName').text = 'RunFacade'
host_items = host_project.find('ItemGroup'); host_items.clear()
E.SubElement(host_items, 'Compile', Include=(here / 'inputs/RunFacade.cs').as_posix())
E.indent(host_project); E.ElementTree(host_project).write(host / 'RunFacade.csproj', encoding='utf-8', xml_declaration=True)
run('facade-host-build', [dotnet, 'build', host / 'RunFacade.csproj', '-c', 'Release', '--configfile', config, '-p:UseSharedCompilation=false', '-v:minimal'])
run('facade-runtime', [dotnet, host / 'bin/Release/net8.0/RunFacade.dll', facade, hashlib.sha256(facade.read_bytes()).hexdigest()])
print('PASS all16 original facade forwards and five source NET8 forwarding/runtime checks', flush=True)

# Preserve original restore closure; record gaps rather than manufacturing runtime packages.
installed = (prefix / 'lib/dotnet/library-packs').resolve()
same = feed.as_posix().casefold() == installed.as_posix().casefold()
tree = E.Element('configuration'); sources = E.SubElement(tree, 'packageSources'); E.SubElement(sources, 'clear')
E.SubElement(sources, 'add', key='candidate', value=feed.as_posix())
if not same: E.SubElement(sources, 'add', key='installed', value=installed.as_posix())
mapping = E.SubElement(tree, 'packageSourceMapping'); candidate = E.SubElement(mapping, 'packageSource', key='candidate')
for name in policies: E.SubElement(candidate, 'package', pattern=name)
E.SubElement(candidate if same else E.SubElement(mapping, 'packageSource', key='installed'), 'package', pattern='*')
E.indent(tree); E.ElementTree(tree).write(out / 'restore.config', encoding='utf-8', xml_declaration=True)
for tfm in ['netstandard1.0', 'netstandard1.3', 'netstandard1.5', 'net8.0', 'net462']:
    folder = out / ('restore-' + tfm); folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
    for n, v in dict(TargetFramework=tfm, EnableDefaultItems='false', DisableImplicitFrameworkReferences='true', AutomaticallyUseReferenceAssemblyPackages='false', NuGetAudit='false', TreatWarningsAsErrors='true').items(): E.SubElement(pg, n).text = v
    items = E.SubElement(tree, 'ItemGroup')
    for name in policies: E.SubElement(items, 'PackageReference', Include=name, Version='[4.3.0]')
    E.indent(tree); E.ElementTree(tree).write(folder / 'Probe.csproj', encoding='utf-8', xml_declaration=True)
    result = run(tfm + '-restore', [dotnet, 'restore', folder / 'Probe.csproj', '--configfile', out / 'restore.config', '-v:minimal'], required=False)
    assets = json.loads((folder / 'obj/project.assets.json').read_text())
    for name in policies:
        assert name + '/4.3.0' in assets['libraries']
        selected_tfm = ('net45' if tfm == 'net462' else 'netstandard1.0') if name == 'System.Reflection.Primitives' else tfm if tfm in ['netstandard1.0', 'netstandard1.3', 'netstandard1.5', 'net462'] else 'netstandard1.5'
        for target in assets['targets'].values():
            selected = target[name + '/4.3.0']
            if tfm == 'net462' and name == 'System.Reflection.Primitives':
                assert not any(p.endswith('.dll') for p in selected.get('compile', {})) and not any(p.endswith('.dll') for p in selected.get('runtime', {}))
            else: assert set(selected['compile']) == {'ref/' + selected_tfm + '/' + name + '.dll'}, (tfm, name, selected)
            if tfm == 'net462' and name == 'System.IO': assert set(selected['runtime']) == {'lib/net462/' + name + '.dll'}
            elif tfm != 'net462': assert not selected.get('runtime') and not selected.get('runtimeTargets'), (tfm, name, selected)
        assert (out / 'cache' / name.lower() / '4.3.0' / (name.lower() + '.4.3.0.nupkg')).read_bytes() == next(p for p in feed.glob('*.nupkg') if p.name.lower() == (name + '.4.3.0.nupkg').lower()).read_bytes()
    diagnostics = assets.get('logs', [])
    assert all(d.get('code') == 'NU1101' for d in diagnostics), diagnostics
    restores[tfm] = dict(exit_code=result.returncode, diagnostics=diagnostics, exact_original_compile_and_runtime_assets_verified=True)
    print(tfm, 'original dependency restore exit', result.returncode, '; diagnostic codes', sorted({d.get('code') for d in diagnostics}), flush=True)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, archives=archives, contracts=contracts,
    total_API_entries=sum(p['API_entries'] for p in contracts.values()), fresh_restore_probes=restores,
    all_original_reference_assets_and_NuGet_semantics_verified=True, all_five_compile_consumers_passed=True,
    all_16_original_NET462_forwarder_names_flags_scopes_and_nesting_verified=True,
    exact_NET462_source_facade_five_core_types_resolved_and_constructor_executed_on_source_NET8=True,
    original_NET462_runtime_execution_verified=False,
    original_dependency_closure_complete=all(r['exit_code'] == 0 for r in restores.values()),
    runtime_provider_packages_supplied=False, historical_runtimes_executed=False, full_dependency_goal_complete=False), indent=2) + '\n')
