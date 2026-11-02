"""Prepare original Roslyn 3.4 NS2 libraries; run with native Windows Python.

This bootstrap does not claim to reproduce the original Arcade build or Toolset.
Published assemblies are metadata baselines only, never compiler references.
"""
from pathlib import Path
import hashlib
import json
import posixpath
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:5])
compiler_exe = sys.argv[5] if len(sys.argv) == 6 else 'csc44.cmd'
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '8bf783851ac159bf7f3d5e1388ce98549352676a80a49eb681e85bcbf6bdc601'
assert not out.exists(), out
out.mkdir()
commit = '82f2e2541478e239dc4b04f231e90dc2b3dcb422'
baseline = json.loads((here / 'inputs/published-metadata.json').read_text())
key = bytes.fromhex((here / 'inputs/MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == '31bf3856ad364e35'
(out / 'Roslyn.public.snk').write_bytes(key)
projects = {
    'Microsoft.CodeAnalysis': 'src/Compilers/Core/Portable/Microsoft.CodeAnalysis.csproj',
    'Microsoft.CodeAnalysis.CSharp': 'src/Compilers/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.csproj',
}
source = out / 'source'
records = {}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == commit
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    def read(name):
        assert name in entries and '..' not in Path(name).parts
        return tar.extractfile(entries[name]).read()
    def imported(project):
        tree = E.fromstring(read(project))
        parent = posixpath.dirname(project)
        selected = []
        for item in tree.findall('.//{*}Compile'):
            assert item.get('Condition') is None
            if item.get('Include'):
                path = item.get('Include').replace('$(MSBuildThisFileDirectory)', parent + '/').replace('\\', '/')
                if not item.get('Include').startswith('$(MSBuildThisFileDirectory)'):
                    path = parent + '/' + path
                path = posixpath.normpath(path)
                assert '$(' not in path and '*' not in path
                selected.append(path)
        for item in tree.findall('.//{*}Import'):
            assert item.get('Condition') is None
            path = posixpath.normpath(parent + '/' + item.get('Project').replace('\\', '/'))
            selected.extend(imported(path))
        return list(dict.fromkeys(selected))
    selected_all = {'.gitattributes', 'eng/Versions.props', 'eng/targets/Settings.props', 'License.txt', 'ThirdPartyNotices.rtf'} & entries.keys()
    for name, project in projects.items():
        parent = posixpath.dirname(project)
        tree = E.fromstring(read(project))
        assert tree.findtext('.//TargetFramework') == 'netstandard2.0'
        selected = {p for p in entries if p.startswith(parent + '/') and p.endswith('.cs')}
        shared_order = imported(project)
        selected |= set(shared_order)
        resources = {p for p in entries if p.startswith(parent + '/') and p.endswith(('.resx', '.xlf'))}
        if name == 'Microsoft.CodeAnalysis':
            resources.add(parent + '/Resources/default.win32manifest')
        selected_all |= selected | resources | {project}
        records[name] = dict(project=project, compile_inputs={p: hashlib.sha256(read(p)).hexdigest() for p in sorted(selected)},
                             resource_inputs={p: hashlib.sha256(read(p)).hexdigest() for p in sorted(resources)},
                             shared_compile_order=shared_order,
                             production_cs_changes=0)
    for p in sorted(selected_all):
        dest = source / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(read(p))

# The compiler reports some partial-type warnings at the first declaration.
# Preserve MSBuild glob order before the explicitly imported shared items;
# ordinal Python sorting changes the scope of original per-file pragmas.
evaluation = out / 'evaluation'; evaluation.mkdir()
localizations = []
for name, record in records.items():
    project = E.Element('Project')
    group = E.SubElement(project, 'ItemGroup')
    E.SubElement(group, 'Compile', Include=(source / record['project']).parent.as_posix() + '/**/*.cs')
    path = evaluation / (name + '.proj')
    E.ElementTree(project).write(path, encoding='utf-8', xml_declaration=True)
    data = subprocess.check_output([str(prefix / 'lib/dotnet/dotnet.exe'), 'msbuild', str(path), '-getItem:Compile'])
    (evaluation / (name + '.json')).write_bytes(data)
    defaults = [Path(p['FullPath']).relative_to(source).as_posix() for p in json.loads(data)['Items']['Compile']]
    order = list(dict.fromkeys(defaults + record['shared_compile_order']))
    assert set(order) == set(record['compile_inputs'])
    record['default_compile_order'] = defaults
    record['compile_inputs'] = {p: record['compile_inputs'][p] for p in order}

support = {'System.Collections.Immutable': '1.5.0', 'System.Reflection.Metadata': '1.6.0',
           'System.Memory': '4.5.3', 'System.Runtime.CompilerServices.Unsafe': '4.5.2',
           'System.Threading.Tasks.Extensions': '4.5.3', 'System.Text.Encoding.CodePages': '4.5.1',
           'System.Buffers': '4.4.0', 'System.Numerics.Vectors': '4.4.0'}
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
support_records = {}
for name, version in support.items():
    package = prefix / 'lib/dotnet/library-packs' / (name.lower() + '.' + version + '.nupkg')
    with zipfile.ZipFile(package) as z:
        candidates = ['ref/netstandard2.0/' + name + '.dll', 'lib/netstandard2.0/' + name + '.dll']
        member = next(p for p in candidates if p in z.namelist())
        dest = out / 'support' / (name + '.dll')
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(z.read(member))
    refs.append(dest)
    support_records[name] = dict(version=version, archive_sha256=sha(package), selected_member=member, selected_sha256=sha(dest))

for name, record in records.items():
    folder = out / name
    folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    values = dict(TargetFramework='netstandard2.0', AssemblyName=name, RootNamespace=name,
                  EnableDefaultItems='false', DisableImplicitFrameworkReferences='true', NoStdLib='true',
                  EnableNETAnalyzers='false', NuGetAudit='false', GenerateAssemblyInfo='false',
                  GenerateTargetFrameworkAttribute='false', GenerateDocumentationFile='true',
                  AllowUnsafeBlocks='true', LangVersion='8.0', Nullable='disable', WarningLevel='4',
                  NoWarn='1573;1591;1701', TreatWarningsAsErrors='true', Features='strict,IOperation',
                  DefineConstants='TRACE;NETSTANDARD;NETSTANDARD2_0' + (';COMPILERCORE' if name == 'Microsoft.CodeAnalysis' else ''),
                  SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile='../Roslyn.public.snk',
                  CscToolPath=compiler.as_posix(), CscToolExe=compiler_exe, Deterministic='true', Optimize='true')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    items = E.SubElement(tree, 'ItemGroup')
    for p in record['compile_inputs']:
        E.SubElement(items, 'Compile', Include=(source / p).as_posix())
    attributes = ['[assembly: System.Reflection.AssemblyVersion("3.4.0.0")]']
    for attr in baseline[name + '.dll']['attributes']:
        if attr['type'] in {'System.Runtime.Versioning.TargetFrameworkAttribute',
                            'System.Runtime.CompilerServices.InternalsVisibleToAttribute',
                            'Microsoft.CodeAnalysis.CommitHashAttribute', 'System.Resources.NeutralResourcesLanguageAttribute'} or attr['type'].startswith('System.Reflection.Assembly'):
            attributes.append('[assembly: ' + attr['type'] + '(' + ','.join(json.dumps(a, ensure_ascii=True) for a in attr['arguments']) + ')]')
    (folder / 'AssemblyInfo.cs').write_text('\n'.join(attributes) + '\n')
    E.SubElement(items, 'Compile', Include='AssemblyInfo.cs')
    for ref in refs:
        entry = E.SubElement(items, 'Reference', Include=ref.stem)
        E.SubElement(entry, 'HintPath').text = ref.as_posix()
        E.SubElement(entry, 'Private').text = 'false'
    if name.endswith('.CSharp'):
        E.SubElement(items, 'ProjectReference', Include='../Microsoft.CodeAnalysis/Build.csproj')
    for p in record['resource_inputs']:
        if p.endswith('.resx'):
            # The archive contains Git's normalized LF blobs. Official Windows
            # checkouts use CRLF under the original '* text=auto' attributes.
            # ResGen preserves these newlines in three English string values.
            projection = folder / 'windows-checkout' / Path(p).name
            projection.parent.mkdir(exist_ok=True)
            projection.write_bytes((source / p).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            record.setdefault('windows_checkout_resource_projections', {})[p] = dict(
                path=projection.relative_to(out).as_posix(), sha256=sha(projection))
            E.SubElement(items, 'EmbeddedResource', Include=projection.as_posix(), LogicalName=name + '.' + Path(p).stem + '.resources')
            ns = {'x': 'urn:oasis:names:tc:xliff:document:1.2'}
            for xlf in sorted((source / p).parent.glob('xlf/' + Path(p).stem + '.*.xlf')):
                translations = E.parse(xlf)
                culture = translations.find('x:file', ns).get('target-language')
                values = {unit.get('id'): ''.join(unit.find('x:target', ns).itertext())
                          for unit in translations.findall('.//x:trans-unit', ns) if unit.find('x:target', ns) is not None}
                localized = E.parse(source / p)
                for value in localized.iter('data'):
                    if value.get('name') in values:
                        value.find('value').text = values[value.get('name')]
                path = folder / (Path(p).stem + '.' + culture + '.resx')
                localized.write(path, encoding='utf-8', xml_declaration=True)
                E.SubElement(items, 'EmbeddedResource', Include=path.name,
                             LogicalName=name + '.' + Path(p).stem + '.' + culture + '.resources',
                             Culture=culture, WithCulture='true')
                localizations.append(dict(assembly=name, culture=culture, source_xlf=xlf.relative_to(source).as_posix(),
                    strings={item.get('name'): item.findtext('value') or '' for item in localized.iter('data')}))
        elif p.endswith('.win32manifest'):
            projection = folder / 'windows-checkout' / Path(p).name
            projection.parent.mkdir(exist_ok=True)
            projection.write_bytes((source / p).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            record.setdefault('windows_checkout_resource_projections', {})[p] = dict(
                path=projection.relative_to(out).as_posix(), sha256=sha(projection))
            E.SubElement(items, 'EmbeddedResource', Include=projection.as_posix(), LogicalName=name + '.Resources.default.win32manifest')
    E.indent(tree)
    E.ElementTree(tree).write(folder / 'Build.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_commit=commit, source_archive_sha256=sha(archive),
    projects=records, support=support_records, compiler_executable=compiler_exe,
    full_original_Arcade_workflow_replayed=False, full_Toolset_packaged=False), indent=2) + '\n')
(out / 'localizations.json').write_text(json.dumps(localizations, indent=2) + '\n')
print('PASS prepared original Roslyn3.4 NS2 libraries:', {n: len(r['compile_inputs']) for n, r in records.items()})
