"""Build original Roslyn 4.4 NS2 compiler/Workspaces projects from pinned source."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(), out
out.mkdir()
here = Path(__file__).resolve().parent
commit = '1ce8866c9de4c2d67351ef6863699dee03b0804a'
archive = root / 'roslyn-4.4.0-1ce8866c.tar.gz'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    return base + '/' + p.resolve().relative_to(root).as_posix()
def posix(p):
    p = p.replace('\\', '/')
    assert p.lower().startswith(base.lower() + '/'), p
    return root / p[len(base) + 1:]
source = out / 'roslyn-source'
# Native extraction avoids the slow per-file MSYS stat path; reject binary inputs.
extract = '''import sys,tarfile,pathlib,json,hashlib
archive,output,commit=sys.argv[1:];source=pathlib.Path(output);source.mkdir();removed=[]
with tarfile.open(archive) as tar:
 assert tar.pax_headers['comment']==commit
 for member in tar:
  if not member.isfile():continue
  name=member.name.partition('/')[2];path=pathlib.PurePosixPath(name)
  assert name and '..' not in path.parts and not path.is_absolute()
  data=tar.extractfile(member).read()
  if path.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip'} or data[:2]==b'MZ':
   removed.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest()));continue
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
(source.parent/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\\n')
'''
subprocess.run(['/clang64/bin/python.exe', '-c', extract, native(archive), native(source), commit], check=True)
def save(tree, path):
    E.indent(tree)
    E.ElementTree(tree).write(path, encoding='utf-8', xml_declaration=True)
key = bytes.fromhex((here / 'inputs/MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == '31bf3856ad364e35'
(out / 'Roslyn.public.snk').write_bytes(key)
names = {
    'Microsoft.CodeAnalysis': 'src/Compilers/Core/Portable/Microsoft.CodeAnalysis.csproj',
    'Microsoft.CodeAnalysis.CSharp': 'src/Compilers/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.csproj',
    'Microsoft.CodeAnalysis.Workspaces': 'src/Workspaces/Core/Portable/Microsoft.CodeAnalysis.Workspaces.csproj',
    'Microsoft.CodeAnalysis.CSharp.Workspaces': 'src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj',
}
wrappers = {}
for name, relative in names.items():
    original = source / relative
    assert 'netstandard2.0' in E.parse(original).findtext('.//TargetFrameworks').split(';')
    folder = out / 'evaluation' / name
    folder.mkdir(parents=True)
    tree = E.fromstring(original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)', native(original.parent) + '/'))
    tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile', 'Import', 'ProjectReference', 'EmbeddedResource'}:
            continue
        for attr in ['Include', 'Remove', 'Update', 'Project']:
            value = item.get(attr, '').replace('\\', '/')
            if value and '$(' not in value and not value.startswith('/') and not (len(value) > 1 and value[1] == ':'):
                item.set(attr, native(original.parent / value))
    save(tree, folder / 'upstream.proj')
    wrapper = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(wrapper, 'PropertyGroup')
    for k, v in dict(Configuration='Release', TargetFramework='netstandard2.0', TargetFrameworkIdentifier='.NETStandard', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false', EnableDefaultItems='false', DotNetBuildFromSource='true', RootNamespace=name, DefineConstants='$(DefineConstants);DOTNET_BUILD_FROM_SOURCE').items():
        E.SubElement(pg, k).text = v
    E.SubElement(wrapper, 'Import', Project=native(source / 'eng/Versions.props'))
    items = E.SubElement(wrapper, 'ItemGroup')
    for path in sorted(original.parent.rglob('*.cs')):
        E.SubElement(items, 'Compile', Include=native(path))
    for path in sorted(original.parent.rglob('*.resx')):
        E.SubElement(items, 'EmbeddedResource', Include=native(path))
    E.SubElement(wrapper, 'Import', Project='upstream.proj')
    path = folder / 'Evaluate.csproj'
    save(wrapper, path)
    wrappers[name] = native(path)
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
sdk = subprocess.check_output(['cygpath', '-am', '/clang64/lib/dotnet/sdk/8.0.131'], text=True).strip()
env = dict(os.environ, MSBuildSDKsPath=sdk + '/Sdks', MSBUILD_EXE_PATH=sdk + '/MSBuild.dll', MSBuildEnableWorkloadResolver='false')
with (out / 'evaluation.log').open('w') as log:
    subprocess.run(['/clang64/lib/dotnet/dotnet.exe', native(root / 'roslyn414-1/evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'), native(out / 'wrappers.json'), native(out / 'evaluated.json')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
evaluated = json.loads((out / 'evaluated.json').read_text())
settings = E.parse(source / 'eng/targets/Settings.props')
def public_key(value):
    if not value:
        return key.hex()
    while value.startswith('$(') and value.endswith(')'):
        value = settings.findtext('.//' + value[2:-1])
        assert value
    assert all(c in '0123456789abcdefABCDEF' for c in value)
    return value
def project(folder, name, tool=False):
    folder.mkdir(parents=True)
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    values = dict(TargetFramework='net8.0' if tool else 'netstandard2.0', AssemblyName=name, RootNamespace=name, OutputType='Exe' if tool else 'Library', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', AllowUnsafeBlocks='true', LangVersion='preview', Nullable='enable', Version='4.4.0', AssemblyVersion='4.4.0.0', FileVersion='4.4.0.0', InformationalVersion='4.4.0+' + commit, IncludeSourceRevisionInInformationalVersion='false', CscToolPath=native(root / 'cdac-bootstrap5/compiler'), CscToolExe='csc50.cmd')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    return tree, pg, E.SubElement(tree, 'ItemGroup')
records = {}
tools = source / 'src/Tools/Source/CompilerGeneratorTools/Source'
for name in ['CSharpSyntaxGenerator', 'BoundTreeGenerator', 'CSharpErrorFactsGenerator', 'IOperationGenerator']:
    folder = out / name
    tree, pg, items = project(folder, name, True)
    files = [p for p in sorted((tools / name).rglob('*.cs')) if p.name not in {'SourceGenerator.cs', 'CachingSourceGenerator.cs'}]
    if name == 'CSharpSyntaxGenerator':
        files += [source / 'src/Compilers' / p for p in ['Core/Portable/Symbols/WellKnownMemberNames.cs', 'CSharp/Portable/Declarations/DeclarationModifiers.cs', 'CSharp/Portable/Syntax/SyntaxKind.cs', 'CSharp/Portable/Syntax/SyntaxKindFacts.cs']]
    for path in files:
        E.SubElement(items, 'Compile', Include=native(path))
    save(tree, folder / 'Build.csproj')
    records[name] = dict(original_cs={p.relative_to(source).as_posix(): sha(p) for p in files}, production_cs_changes=0, tool=True)
localizations = []
def resource(folder, items, path, metadata, name):
    if path.suffix != '.resx':
        logical = metadata.get('LogicalName') or name + '.' + path.relative_to((source / names[name]).parent).as_posix().replace('/', '.')
        E.SubElement(items, 'EmbeddedResource', Include=native(path), LogicalName=logical)
        return
    ns = metadata.get('Namespace') or evaluated[name]['properties']['RootNamespace']
    cls = metadata.get('ClassName') or path.stem
    if '.' in cls:
        ns, _, cls = cls.rpartition('.')
    logical = (metadata.get('LogicalName') or metadata.get('ManifestResourceName') or ns + '.' + path.stem).removesuffix('.resources')
    code = ['#nullable enable', 'namespace ' + ns + ' { internal static class ' + cls + ' {', 'internal static global::System.Resources.ResourceManager ResourceManager {get;} = new global::System.Resources.ResourceManager(' + json.dumps(logical) + ', typeof(' + cls + ').Assembly);', 'internal static global::System.Globalization.CultureInfo? Culture {get;set;}']
    for item in E.parse(path).iter('data'):
        key_name = item.get('name')
        field = re.sub(r'[^A-Za-z0-9_]', '_', key_name)
        assert field.isidentifier(), field
        code.append('internal static string @' + field + ' => ResourceManager.GetString(' + json.dumps(key_name) + ', Culture)!;')
    code.append('}}')
    generated = folder / (ns + '.' + cls + '.Generated.cs')
    generated.write_text('\n'.join(code) + '\n')
    E.SubElement(items, 'Compile', Include=generated.name)
    E.SubElement(items, 'EmbeddedResource', Include=native(path), LogicalName=logical + '.resources')
    localizations.append(dict(assembly=name, resource=logical, culture='', strings={e.get('name'): e.findtext('value') or '' for e in E.parse(path).iter('data')}))
    xns = {'x': 'urn:oasis:names:tc:xliff:document:1.2'}
    for xlf_path in sorted((path.parent / 'xlf').glob(path.stem + '.*.xlf')):
        xlf = E.parse(xlf_path)
        culture = xlf.find('x:file', xns).get('target-language')
        translations = {e.get('id'): ''.join(e.find('x:target', xns).itertext()) for e in xlf.findall('.//x:trans-unit', xns) if e.find('x:target', xns) is not None}
        localized = E.parse(path)
        for e in localized.iter('data'):
            if e.get('name') in translations:
                e.find('value').text = translations[e.get('name')]
        target = folder / (logical + '.' + culture + '.resx')
        localized.write(target, encoding='utf-8', xml_declaration=True)
        E.SubElement(items, 'EmbeddedResource', Include=target.name, LogicalName=logical + '.' + culture + '.resources', Culture=culture, WithCulture='true')
        localizations.append(dict(assembly=name, resource=logical, culture=culture, strings={e.get('name'): e.findtext('value') or '' for e in localized.iter('data')}))
resolved = {'System.Collections.Immutable': '9.0.0', 'System.Reflection.Metadata': '9.0.0', 'System.Memory': '4.6.2', 'System.Runtime.CompilerServices.Unsafe': '6.1.1', 'System.Threading.Tasks.Extensions': '4.6.2', 'System.Text.Encoding.CodePages': '9.0.0', 'System.Composition': '9.0.0', 'Microsoft.Bcl.AsyncInterfaces': '9.0.0', 'System.IO.Pipelines': '9.0.0', 'Humanizer.Core': '2.14.1'}
project_ids = {n: ('Microsoft.CodeAnalysis.Common' if n == 'Microsoft.CodeAnalysis' else 'Microsoft.CodeAnalysis.Workspaces.Common' if n == 'Microsoft.CodeAnalysis.Workspaces' else n) for n in names}
for name, relative in names.items():
    data = evaluated[name]
    defines = data['properties']['DefineConstants']
    assert 'DEBUG' not in defines.split(';'), defines
    folder = out / name
    tree, pg, items = project(folder, name)
    for k, v in dict(RootNamespace=data['properties']['RootNamespace'], DefineConstants=defines, SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile='../Roslyn.public.snk', PackageId=project_ids[name], PackageLicenseExpression='MIT', RepositoryUrl='https://github.com/dotnet/roslyn', RepositoryCommit=commit, NoWarn=data['properties']['NoWarn']).items():
        E.SubElement(pg, k).text = v
    selected = list(dict.fromkeys(posix(e['full_path']) for e in data['items']['Compile']))
    if name == 'Microsoft.CodeAnalysis.CSharp':
        selected = [p for p in selected if not p.is_relative_to((source / relative).parent / 'Generated')]
        E.SubElement(items, 'Compile', Include=native(out / 'generated') + '/*.cs')
    if name == 'Microsoft.CodeAnalysis.Workspaces':
        assert not any('/Storage/SQLite/' in str(p) for p in selected)
    assert selected and all(p.is_file() for p in selected)
    for path in selected:
        E.SubElement(items, 'Compile', Include=native(path))
    minimums, dependencies = {}, {}
    for entry in data['items']['PackageReference']:
        ident = entry['identity']
        if ident == 'NETStandard.Library':
            continue
        assert ident in resolved, (name, ident)
        minimums[ident] = entry['metadata']['Version']
        dependencies[ident] = resolved[ident]
    for entry in data['items']['ProjectReference']:
        ident = Path(entry['full_path'].replace('\\', '/')).stem
        if ident == 'CSharpSyntaxGenerator':
            assert entry['metadata']['ReferenceOutputAssembly'] == 'false'
            continue
        assert ident in project_ids, (name, ident)
        dependencies[project_ids[ident]] = '4.4.0'
    for ident, version in dependencies.items():
        E.SubElement(items, 'PackageReference', Include=ident, Version='[' + version + ']', **({'PrivateAssets': 'compile'} if ident == 'Humanizer.Core' else {}))
    resources = {posix(e['full_path']): e['metadata'] for e in data['items']['EmbeddedResource']}
    for path, metadata in resources.items():
        resource(folder, items, path, metadata, name)
    original = E.parse(source / relative)
    friends = []
    for kind in ['InternalsVisibleTo', 'RestrictedInternalsVisibleTo']:
        raw = {e.get('Include'): e.attrib for e in original.iter(kind)}
        for item in data['items'][kind]:
            metadata = raw.get(item['identity'], item['metadata'])
            friends.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo(' + json.dumps(item['identity'] + ', PublicKey=' + public_key(metadata.get('Key', ''))) + ')]')
            if kind == 'RestrictedInternalsVisibleTo':
                namespace = metadata.get('Namespace') or 'Microsoft.CodeAnalysis.ExternalAccess.' + metadata['Partner'] + '.Api'
                friends.append('[assembly: System.Runtime.CompilerServices.RestrictedInternalsVisibleTo(' + json.dumps(item['identity']) + ', ' + json.dumps(namespace) + ')]')
    if name == 'Microsoft.CodeAnalysis.CSharp':
        friends.append('[assembly: Microsoft.CodeAnalysis.CommitHash(' + json.dumps(commit) + ')]')
    (folder / 'Friends.Generated.cs').write_text('\n'.join(dict.fromkeys(friends)) + '\n')
    E.SubElement(items, 'Compile', Include='Friends.Generated.cs')
    for filename in ['License.txt', 'THIRD-PARTY-NOTICES.txt']:
        E.SubElement(items, 'None', Include=native(source / filename), Pack='true', PackagePath='/')
    capture = E.SubElement(tree, 'Target', Name='CaptureActualCompilerInputs', BeforeTargets='CoreCompile')
    for kind in ['Compile', 'ReferencePath', 'Analyzer']:
        E.SubElement(capture, 'WriteLinesToFile', File='$(IntermediateOutputPath)' + kind + '.txt', Lines='@(' + kind + "->'%(FullPath)')", Overwrite='true')
    save(tree, folder / 'Build.csproj')
    records[name] = dict(original_project=relative, original_project_sha256=sha(source / relative), original_cs={p.relative_to(source).as_posix(): sha(p) for p in selected}, original_resources={p.relative_to(source).as_posix(): sha(p) for path in resources for p in [path, *sorted((path.parent / 'xlf').glob(path.stem + '.*.xlf'))]}, original_package_minimums=minimums, resolved_dependencies=dependencies, friend_attributes=list(dict.fromkeys(friends)), production_cs_changes=0, configuration='Release', framework='netstandard2.0')
platform = out / 'platform-feed'
platform.mkdir()
shutil.copyfile('/clang64/lib/dotnet/library-packs/microsoft.netcore.platforms.1.1.2.nupkg', platform / 'microsoft.netcore.platforms.1.1.2.nupkg')
config = E.Element('configuration')
feeds = E.SubElement(config, 'packageSources')
E.SubElement(feeds, 'clear')
(out / 'feed').mkdir()
for i, path in enumerate([out / 'feed', root / 'runtime9-ns20-2/feed', root / 'humanizer-ns20-1/feed', root / 'maintenance20-1/feed', root / 'netstandard20-2/feed', platform]):
    E.SubElement(feeds, 'add', key='source' + str(i), value=native(path))
save(config, out / 'NuGet.config')
(out / 'source-inputs.json').write_text(json.dumps(dict(roslyn_version='4.4.0', roslyn_commit=commit, source_archive_sha256=sha(archive), projects=records, configuration='Release', full_dependency_goal_complete=False), indent=2) + '\n')
(out / 'localization.json').write_text(json.dumps(localizations, ensure_ascii=False, indent=2) + '\n')
print('Prepared original Roslyn4.4', {n: len(e['original_cs']) for n, e in records.items()}, 'resource sets', len(localizations), flush=True)
