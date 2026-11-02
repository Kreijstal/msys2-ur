"""Build the original Immutable1.5/Metadata1.6 library profiles from source."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out, prefix, compiler, additional = (Path(p).resolve() for p in sys.argv[1:6])
only_immutable = '--only-immutable' in sys.argv[6:]
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
commit = '30ab651fcb4354552bd4891619a0bdd81e0ebdbf'
assert sha(archive) == 'a886ecc798d92fa1183eb127f95ceb47270be7a53fcae51e7f391523c261e586'
names = ['System.Collections.Immutable'] + ([] if only_immutable else ['System.Reflection.Metadata'])
source = out / 'source'; hashes = {}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == commit
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    selected = {'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT', 'dir.props', 'src/dir.props', 'src/Common/src/System/SR.cs'}
    for name in names:
        folder = 'src/' + name + '/src/'
        selected |= {p for p in entries if p.startswith(folder) and p.endswith(('.cs', '.csproj', '.resx'))}
        project = E.fromstring(tar.extractfile(entries[folder + name + '.csproj']).read())
        for item in project.findall('.//{*}Compile'):
            path = item.get('Include').replace('\\', '/')
            if path.startswith('$(CommonPath)/'):
                selected.add(path.replace('$(CommonPath)', 'src/Common/src'))
    for path in sorted(selected):
        data = tar.extractfile(entries[path]).read()
        assert data[:2] != b'MZ'
        target = source / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        hashes[path] = sha(target)
key = here / 'inputs/Microsoft.snk'
assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
legacy = prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts'
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
commands, profiles = [], {}
def run(label, command):
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout)
    commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])

for name in names:
    frameworks = ['netstandard1.0', 'netstandard1.3', 'netstandard2.0'] if name.endswith('Immutable') else ['netstandard1.1', 'netstandard2.0']
    original = source / 'src' / name / 'src' / (name + '.csproj')
    for framework in frameworks:
        baseline = json.loads((here / 'inputs' / (name + '-' + framework + '-metadata.json')).read_text())[name + '.dll']
        folder = out / name / framework; folder.mkdir(parents=True)
        upstream = E.parse(original).getroot()
        for element in upstream.iter(): element.tag = element.tag.rsplit('}', 1)[-1]
        for child in list(upstream):
            if child.tag == 'Import': upstream.remove(child)
        for group in upstream.findall('ItemGroup'):
            for item in list(group):
                if item.tag in {'Reference', 'ProjectReference'}: group.remove(item)
                else:
                    for attr in ['Include', 'Remove', 'Update']:
                        if item.get(attr):
                            path = item.get(attr).replace('\\', '/')
                            item.set(attr, path if path.startswith('$(CommonPath)') else original.parent.as_posix() + '/' + path)
        E.indent(upstream); E.ElementTree(upstream).write(folder / 'upstream.proj', encoding='utf-8', xml_declaration=True)
        if framework == 'netstandard2.0':
            refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
            assert len(refs) == 113
        else:
            required = {r.split(', Version=')[0]: r.split(', Version=')[1].split(',')[0] for r in baseline['references'] if not r.startswith('System.Collections.Immutable,')}
            variants = {}
            for ident in matrix:
                ident_name, version = ident.split('/')
                variants.setdefault(ident_name, []).append(version)
            allowed = set(required) | {p.get('Include') for p in E.parse(original).findall('.//{*}Reference')}
            if name.endswith('Immutable') and framework == 'netstandard1.0': allowed.discard('System.Runtime.InteropServices')
            if framework == 'netstandard1.1': allowed.discard('System.IO.MemoryMappedFiles')
            selected = {n: required.get(n, sorted(v, key=lambda s: tuple(map(int, s.split('.'))), reverse=framework == 'netstandard1.3')[0]) for n, v in variants.items() if n in allowed}
            refs = [legacy / n / v / (n + '.dll') for n, v in sorted(selected.items())]
            for n in ['System.IO.Compression', 'System.Reflection.Extensions', 'System.Text.Encoding.Extensions']:
                if n in required: refs.append(additional / (n + '.dll'))
            if name == 'System.Reflection.Metadata':
                refs = [p for p in refs if p.name != 'System.Runtime.InteropServices.dll']
                refs.append(additional / 'System.Runtime.InteropServices.dll')
        if name == 'System.Reflection.Metadata':
            imm_framework = 'netstandard1.0' if framework == 'netstandard1.1' else framework
            refs.append(out / 'System.Collections.Immutable' / imm_framework / 'bin/Release/System.Collections.Immutable.dll')
        assert refs and all(p.is_file() for p in refs), [(str(p), p.is_file()) for p in refs]
        version = baseline['identity'].split('Version=')[1].split(',')[0]
        attributes = ['[assembly: System.Reflection.AssemblyVersion(' + json.dumps(version) + ')]']
        for attr in baseline['attributes']:
            kind = attr['type']
            if kind in {'System.Runtime.CompilerServices.ExtensionAttribute', 'System.Runtime.CompilerServices.CompilationRelaxationsAttribute',
                        'System.Runtime.CompilerServices.RuntimeCompatibilityAttribute', 'System.Diagnostics.DebuggableAttribute'}: continue
            values = []
            for arg in attr['arguments']:
                if kind == 'System.CLSCompliantAttribute': values.append(arg.lower())
                elif kind == 'System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute':
                    values.append('(System.Runtime.InteropServices.DllImportSearchPath)' + arg)
                else: values.append(json.dumps(arg))
            attributes.append('[assembly: ' + kind + '(' + ','.join(values) + ')]')
        (folder / 'Version.cs').write_text('\n'.join(attributes) + '\n')
        tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); pg = E.SubElement(tree, 'PropertyGroup')
        properties = dict(TargetFramework=framework, TargetGroup='netstandard' if framework == 'netstandard2.0' else framework,
            ConfigurationGroup='Release', Platform='AnyCPU', AssemblyName=name, RootNamespace=name, DisableImplicitFrameworkReferences='true',
            NoStdLib='true', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', GenerateAssemblyInfo='false',
            GenerateTargetFrameworkAttribute='false', LangVersion='7.3', Nullable='disable', TreatWarningsAsErrors='true', WarningLevel='4',
            NoWarn='1701;1702;1573;1591', SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile=key.as_posix(),
            CommonPath=(source / 'src/Common/src').as_posix(), AllowUnsafeBlocks='true', UseSharedCompilation='false',
            CscToolPath=compiler.as_posix(), CscToolExe='csc44.cmd', Optimize='true', DebugType='portable',
            AppendTargetFrameworkToOutputPath='false', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false')
        for k, v in properties.items(): E.SubElement(pg, k).text = v
        E.SubElement(tree, 'Import', Project='upstream.proj')
        E.SubElement(E.SubElement(tree, 'PropertyGroup'), 'DocumentationFile').text = (folder / 'bin/Release' / (name + '.xml')).as_posix()
        items = E.SubElement(tree, 'ItemGroup')
        for p in refs: E.SubElement(items, 'Reference', Include=p.stem, HintPath=p.as_posix(), Private='false')
        E.SubElement(items, 'Compile', Include=(source / 'src/Common/src/System/SR.cs').as_posix())
        E.SubElement(items, 'Compile', Include='Version.cs'); E.SubElement(items, 'Compile', Include='SR.Generated.cs')
        resource = original.parent / 'Resources/Strings.resx'; logical = 'FxResources.' + name + '.SR'
        E.SubElement(items, 'EmbeddedResource', Include=resource.as_posix(), LogicalName=logical + '.resources')
        values = {v.get('name'): v.findtext('value') for v in E.parse(resource).findall('data')}
        accessor = ['namespace FxResources.' + name + ' {internal static class SR {}}',
                    'namespace System {internal partial class SR {private static System.Type ResourceType => typeof(' + logical + ');']
        accessor += ['internal static string @' + k + ' => GetResourceString(' + json.dumps(k) + ',null);' for k in values]
        (folder / 'SR.Generated.cs').write_text('\n'.join(accessor + ['}}']) + '\n')
        target = E.SubElement(tree, 'Target', Name='CaptureInputs', BeforeTargets='CoreCompile')
        for kind in ['Compile', 'ReferencePath', 'Analyzer']:
            E.SubElement(target, 'WriteLinesToFile', File=(folder / (kind + '.txt')).as_posix(), Lines='@(' + kind + "->'%(FullPath)')", Overwrite='true')
        E.SubElement(target, 'WriteLinesToFile', File=(folder / 'policy.txt').as_posix(),
                     Lines='$(TargetFramework)|$(TargetGroup)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)', Overwrite='true')
        E.indent(tree); E.ElementTree(tree).write(folder / 'Library.csproj', encoding='utf-8', xml_declaration=True)
        run(name + '-' + framework, [prefix / 'lib/dotnet/dotnet.exe', 'build', folder / 'Library.csproj', '-c', 'Release', '--configfile', out / 'NuGet.config', '-v:minimal'])
        profiles[name + '/' + framework] = dict(DLL_sha256=sha(folder / 'bin/Release' / (name + '.dll')),
            reference_sha256={p.as_posix(): sha(p) for p in refs}, original_project=original.relative_to(source).as_posix())
        print('PASS original library profile', name, framework, flush=True)
(out / 'results.json').write_text(json.dumps(dict(source_commit=commit, source_archive_sha256=sha(archive),
    original_file_sha256=hashes, production_CSharp_changes=0, profiles=profiles, commands=commands,
    original_buildtools_replayed=False, complete_dependency_goal=False), indent=2) + '\n')
