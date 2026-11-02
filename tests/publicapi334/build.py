"""Build original NS2 PublicApiAnalyzers with disclosed source Roslyn4.4 bootstrap references."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tarfile, zipfile, xml.etree.ElementTree as E
from port import port_source

snapshot, inputs_file, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(snapshot) == '54427e4c1b4dd6e74edbdf3e11eda059f13ae7051db91709e1d6b7847433d398'
with tarfile.open(snapshot) as t:
    t.extractall(out / 'snapshot', filter='data')
source = out / 'snapshot/source'
manifest = json.loads((out / 'snapshot/source-inputs.json').read_text())
for rel, h in manifest['files'].items():
    assert sha(source / rel) == h, rel
inputs = json.loads(inputs_file.read_text())
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
deps = out / 'dependencies'
deps.mkdir()
binary = out / 'bin'
binary.mkdir()
assets = []
for package, version in [('Microsoft.CodeAnalysis.Common', '4.4.0'), ('Microsoft.CodeAnalysis.Workspaces.Common', '4.4.0'),
        ('System.Collections.Immutable', '9.0.0'), ('System.Reflection.Metadata', '9.0.0'), ('System.Memory', '4.6.2'),
        ('System.Runtime.CompilerServices.Unsafe', '6.1.1'), ('System.Composition.AttributedModel', '9.0.0'),
        ('System.Composition.Runtime', '9.0.0'), ('System.Threading.Tasks.Extensions', '4.6.2')]:
    archive = prefix / 'lib/dotnet/library-packs' / (package.lower() + '.' + version + '.nupkg')
    with zipfile.ZipFile(archive) as z:
        members = [m for m in z.namelist() if m.startswith('lib/netstandard2.0/') and m.endswith('.dll') and m.count('/') == 2]
        assert len(members) == 1, (package, members)
        target = deps / Path(members[0]).name
        target.write_bytes(z.read(members[0]))
    assets.append(dict(package=package, version=version, source_archive_sha256=sha(archive), member=members[0], sha256=sha(target)))
    refs = [p for p in refs if p.name != target.name] + [target]
key = out / 'public.snk'
key.write_bytes(bytes.fromhex((here / 'MicrosoftShared.pubkey.hex').read_text()))
assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == '31bf3856ad364e35'
commands = []
def run(label, cmd, root=host10.parent):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(root), DOTNET_ROOT_X64=native(root)), timeout=240)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)
records = {}
for label, entry in inputs.items():
    name = entry['assembly']
    folder = out / label
    folder.mkdir()
    originals = [source / rel for rel in entry['sources']]
    assert entry['original_framework'] == 'netstandard2.0' and entry['original_MicrosoftCodeAnalysisVersion'] == '1.2.1'
    for rel, h in {**entry['sources'], **entry['original_imports'], **entry['resource_files']}.items():
        assert sha(source / rel) == h == manifest['files'][rel]
    generated = []
    compile_sources = []
    source_ports = {}
    for original in originals:
        text = original.read_text(encoding='utf-8-sig')
        ported, reasons = port_source(original.name, text)
        if ported != text:
            target = folder / 'ports' / original.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(ported, encoding='utf-8')
            compile_sources.append(target)
            source_ports[original.relative_to(source).as_posix()] = dict(
                original_sha256=sha(original), compiled_sha256=sha(target), reasons=reasons)
        else:
            compile_sources.append(original)
    resource_args = []
    if entry['resource_files']:
        project = E.Element('Project')
        E.SubElement(project, 'UsingTask', TaskName='GenerateResource', AssemblyFile=native(host8.parent / 'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'))
        target = E.SubElement(project, 'Target', Name='Generate')
        for rel in entry['resource_files']:
            resx = source / rel
            logical = 'Microsoft.CodeAnalysis.PublicApiAnalyzers.' + resx.stem
            resource = folder / (resx.stem + '.resources')
            E.SubElement(target, 'GenerateResource', Sources=native(resx), OutputResources=native(resource), ExecuteAsTool='false')
            values = [n.get('name') for n in E.parse(resx).findall('data')]
            wrapper = folder / (resx.stem + '.g.cs')
            wrapper.write_text('#nullable enable\nnamespace Microsoft.CodeAnalysis.PublicApiAnalyzers { internal static partial class ' + resx.stem + ' {\n' +
                'internal static System.Resources.ResourceManager ResourceManager {get;} = new System.Resources.ResourceManager(' + json.dumps(logical) + ',typeof(' + resx.stem + ').Assembly);\n' +
                'internal static System.Globalization.CultureInfo? Culture {get;set;}\n' +
                '\n'.join('internal static string @' + n + ' => ResourceManager.GetString(' + json.dumps(n) + ',Culture)!;' for n in values) + '\n}}\n')
            generated.append(wrapper)
            resource_args.append('/resource:"' + native(resource) + '",' + logical + '.resources')
        E.ElementTree(project).write(folder / 'Resources.proj', encoding='utf-8', xml_declaration=True)
        run(label + '-resources', [host8, 'msbuild', folder / 'Resources.proj', '-t:Generate', '-nologo'], host8.parent)
    info = folder / 'AssemblyInfo.g.cs'
    attributes = ['[assembly:System.Reflection.AssemblyVersion("3.3.8.6701")]',
        '[assembly:System.Reflection.AssemblyFileVersion("3.3.8.6701")]',
        '[assembly:System.Reflection.AssemblyInformationalVersion("3.3.4-beta1.23067.1+source.22ea6422f85b05ca0793cc3b76375487be407f5d")]',
        '[assembly:System.Runtime.Versioning.TargetFramework(".NETStandard,Version=v2.0")]',
        '[assembly:System.Resources.NeutralResourcesLanguage("en")]']
    for friend in ['Microsoft.CodeAnalysis.PublicApiAnalyzers.CodeFixes', 'Microsoft.CodeAnalysis.PublicApiAnalyzers.UnitTests']:
        attributes.append('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo(' + json.dumps(friend + ', PublicKey=' + key.read_bytes().hex()) + ')]')
    info.write_text('\n'.join(attributes) + '\n')
    generated.append(info)
    args = ['/nostdlib+', '/warnaserror+', '/target:library', '/langversion:preview', '/nullable:enable', '/features:strict,flow-analysis',
        '/optimize+', '/deterministic+', '/debug:portable', '/publicsign+', '/keyfile:"' + native(key) + '"',
        '/out:"' + native(binary / (name + '.dll')) + '"', '/doc:"' + native(binary / (name + '.xml')) + '"',
        '/nowarn:1701,1702,1705,1573,1591,1712', '/define:TRACE;NETSTANDARD;NETSTANDARD2_0;NETSTANDARD2_0_OR_GREATER']
    selected = refs + ([binary / 'Microsoft.CodeAnalysis.PublicApiAnalyzers.dll'] if label == 'codefixes' else [])
    args += ['/reference:"' + native(p) + '"' for p in selected] + resource_args
    args += ['"' + native(p) + '"' for p in compile_sources + generated]
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    run(label + '-compile', [host10, compiler, '-noconfig', '@' + native(rsp)])
    records[label] = entry | dict(original_source_changes=len(source_ports), source_ports=source_ports, original_framework_preserved=True,
        declared_Roslyn_version='1.2.1', original_source_Roslyn_capability_guards_preserved=True, bootstrap_reference_Roslyn_version_override='4.4.0', bootstrap_source_Roslyn_version='4.4.0', legacy_Roslyn12_host_compatibility_verified=False,
        generated_source_sha256={p.name: sha(p) for p in generated}, reference_sha256={native(p): sha(p) for p in selected},
        output_sha256={ext: sha(binary / (name + '.' + ext)) for ext in ['dll', 'pdb', 'xml']})
    print('PASS', name, len(originals), 'original source inputs; original NS2, source Roslyn4.4 bootstrap', flush=True)
(out / 'results.json').write_text(json.dumps(dict(projects=records, commands=commands, dependency_assets=assets,
    original_NETStandard2_profiles_preserved=True, compiler_warnings_as_errors=True, bootstrap_source_Roslyn44_references_disclosed=True,
    original_Roslyn12_minimum_host_compatibility_verified=False, formal_package_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
