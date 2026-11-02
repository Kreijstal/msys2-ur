"""Prepare original JSON10 and its original runtime dependencies for supported net8.0."""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:])
generators=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs')
assert not out.exists(), out
out.mkdir()
here = Path(__file__).resolve().parent
subprocess.run(['/clang64/bin/python.exe',subprocess.check_output(['cygpath','-am',str(here/'extract-source.py')],text=True).strip(),subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()],check=True)
subprocess.run(['/usr/bin/python3',str(here/'prepare-version.py'),str(root)],check=True)
source = root / 'r'
libs = source / 'src/libraries'
archive = root / 'runtime-v10.0.5.tar.gz'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
base = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(p):
    p=Path(p).resolve()
    if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
def posix(p):
    p = p.replace('\\', '/')
    assert p.lower().startswith(base.lower() + '/'), p
    return root / p[len(base) + 1:]
def save(tree, path):
    E.indent(tree)
    E.ElementTree(tree).write(path, encoding='utf-8', xml_declaration=True)
projects = {
    'System.Text.Encodings.Web': libs / 'System.Text.Encodings.Web/src/System.Text.Encodings.Web.csproj',
    'System.IO.Pipelines': libs / 'System.IO.Pipelines/src/System.IO.Pipelines.csproj',
    'System.Text.Json': libs / 'System.Text.Json/src/System.Text.Json.csproj',
}
shared = E.Element('Project')
for item in E.parse(libs / 'Directory.Build.targets').getroot():
    text = E.tostring(item, encoding='unicode')
    if item.tag in {'ItemGroup', 'Choose'} and any(s in text for s in ['NullableAttributes.cs', 'ExceptionPolyfills.cs', 'PlatformAttributes.cs', 'System\\ObsoleteAttribute.cs', 'System\\Index.cs']):
        shared.append(copy.deepcopy(item))
assert len(shared) == 5
save(shared, out / 'original-shared-sources.targets')
wrappers, key_policies = {}, {}
for name, original in projects.items():
    folder = out / 'evaluation' / name
    folder.mkdir(parents=True)
    tree = E.fromstring(original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)', native(original.parent) + '/'))
    tree.attrib.pop('Sdk')
    for item in tree.iter():
        if item.tag not in {'Compile', 'EmbeddedResource', 'ProjectReference', 'Import'}:
            continue
        for attr in ['Include', 'Remove', 'Update', 'Project']:
            value = item.get(attr, '').replace('\\', '/')
            if value and '$(' not in value and not value.startswith('/') and not (len(value) > 1 and value[1] == ':'):
                item.set(attr, native(original.parent / value))
    if name == 'System.Text.Json.SourceGeneration':
        imported = original.parent / 'System.Text.Json.SourceGeneration.targets'
        imported_tree = E.fromstring(imported.read_text(encoding='utf-8-sig'))
        for item in imported_tree.iter('Compile'):
            value = item.get('Include', '').replace('\\', '/')
            if value and '$(' not in value:
                item.set('Include', native(imported.parent / value))
        save(imported_tree, folder / imported.name)
        next(tree.iter('Import')).set('Project', native(folder / imported.name))
    save(tree, folder / 'upstream.proj')
    key, platform, policies = 'Open', False, []
    for parent in [libs, *[libs.joinpath(*original.parent.relative_to(libs).parts[:i]) for i in range(1, len(original.parent.relative_to(libs).parts) + 1)]]:
        policy = parent / 'Directory.Build.props'
        if policy.is_file():
            policies.append(policy.relative_to(source).as_posix())
            parsed = E.parse(policy)
            own_key = parsed.findtext('.//StrongNameKeyId')
            if own_key in {'Open', 'Microsoft'}:
                key = own_key
            if parsed.findtext('.//IncludePlatformAttributes') == 'true':
                platform = True
    key_policies[name] = dict(key=key, files=policies, include_platform_attributes=platform)
    wrapper = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(wrapper, 'PropertyGroup')
    values = dict(Configuration='Release', DotNetBuildSourceOnly='true', TargetFramework='net8.0', TargetFrameworkIdentifier='.NETCoreApp', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false', EnableDefaultItems='false', EnableDefaultCompileItems='false', EnableDefaultEmbeddedResourceItems='false', NetCoreAppCurrent='net10.0', NetCoreAppPrevious='net9.0', NetCoreAppMinimum='net8.0', NetCoreAppToolCurrent='net8.0', CommonPath=native(libs / 'Common/src') + '/', LibrariesProjectRoot=native(libs) + '/', CoreLibSharedDir=native(libs / 'System.Private.CoreLib/src') + '/', IncludePlatformAttributes='true' if platform else 'false', StrongNameKeyId=key, DefaultLanguageSourceExtension='.cs', RootNamespace=name, AssemblyName=name, Nullable='enable')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    E.SubElement(wrapper, 'Import', Project=native(source / 'eng/Versions.props'))
    items = E.SubElement(wrapper, 'ItemGroup')
    # JSON explicitly lists its complete source set in the original imported targets.
    # All three original implementation projects explicitly select their sources.
    E.SubElement(wrapper, 'Import', Project='upstream.proj')
    E.SubElement(wrapper, 'Import', Project=native(out / 'original-shared-sources.targets'))
    path = folder / 'Evaluate.csproj'
    save(wrapper, path)
    wrappers[name] = native(path)
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
subprocess.run(['/usr/bin/python3',str(here/'evaluate.py'),str(root),str(out)],check=True)
evaluated = json.loads((out / 'evaluated.json').read_text())
for key in ['Microsoft', 'Open']:
    (out / (key + '.pubkey')).write_bytes(bytes.fromhex((here / 'inputs' / (key + '.pubkey.hex')).read_text()))
records, localizations = {}, []
for name, original in projects.items():
    folder = out / name
    folder.mkdir()
    data = evaluated[name]
    assert 'DEBUG' not in data['properties']['DefineConstants'].split(';')
    selected = list(dict.fromkeys(posix(e['full_path']) for e in data['items']['Compile']))
    assert selected and all(p.is_file() for p in selected), (name, [str(p) for p in selected if not p.is_file()])
    resource = original.parent / 'Resources/Strings.resx'
    if name.startswith('Microsoft.Interop.') and name != 'Microsoft.Interop.JavaScript.JSImportGenerator':
        resource = libs / 'System.Runtime.InteropServices/gen/Common/Resources/Strings.resx'
    if resource.is_file():
        selected.append(libs / 'Common/src/System/SR.cs')
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    key = key_policies[name]['key']
    for k, v in dict(TargetFramework='net8.0', AssemblyName=name, RootNamespace=data['properties']['RootNamespace'], Version='10.0.5', AssemblyVersion='10.0.0.0', FileVersion=(root/'file-version.txt').read_text().strip(), InformationalVersion='10.0.5+081d220c0a773ffb7c6bea6b48727833576a65ef', IncludeSourceRevisionInInformationalVersion='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', AllowUnsafeBlocks='true', LangVersion='preview', DefineConstants=data['properties']['DefineConstants'], NoWarn=data['properties']['NoWarn'], CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')), CscToolExe='csc50.cmd', SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile=native(out / (key + '.pubkey')), CopyLocalLockFileAssemblies='true', IsPackable='true', GenerateDocumentationFile='true', GenerateAssemblyConfigurationAttribute='false', GenerateNeutralResourcesLanguageAttribute='false', IsSourceProject='true', CLSCompliant='true', PackageId=name, PackageLicenseExpression='MIT', PackageReadmeFile='PACKAGE.md', RepositoryUrl='https://github.com/dotnet/runtime', RepositoryCommit='081d220c0a773ffb7c6bea6b48727833576a65ef', IncludeSymbols='false', IncludeSource='false').items():
        E.SubElement(pg, k).text = v
    items = E.SubElement(tree, 'ItemGroup')
    E.SubElement(pg,'PackageDescription').text=E.parse(original).findtext('.//PackageDescription')
    E.SubElement(items,'None',Include=native(original.parent/'PACKAGE.md'),Pack='true',PackagePath='/')
    for filename in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:
        E.SubElement(items,'None',Include=native(source/filename),Pack='true',PackagePath='/')
    # The original source policy defaults IsTrimmable to true. Retain the metadata
    # without substituting a binary SDK8 ILLink producer for the source ILLink10.
    E.SubElement(items,'AssemblyMetadata',Include='IsTrimmable',Value='True')
    for path in selected:
        E.SubElement(items, 'Compile', Include=native(path))
    dependencies = {}
    for entry in data['items']['PackageReference']:
        ident = entry['identity']
        if ident == 'NETStandard.Library':
            continue
        assert ident in {'Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp.Workspaces'}, (name, ident)
        dependencies[ident] = entry['metadata']['Version']
        E.SubElement(items, 'PackageReference', Include=ident, Version='[' + dependencies[ident] + ']')
    project_dependencies = []
    for entry in data['items']['ProjectReference']:
        path = posix(entry['full_path'])
        if entry['metadata'].get('ReferenceOutputAssembly', '').lower() == 'false':
            if entry['metadata'].get('OutputItemType') == 'Analyzer':
                assert path.name == 'System.Text.RegularExpressions.Generator.csproj'
                E.SubElement(items, 'Analyzer', Include=native(generators / 'System.Text.RegularExpressions.Generator.dll'))
                E.SubElement(items, 'Analyzer', Include=native(generators / 'Microsoft.Interop.SourceGeneration.dll'))
            continue
        referenced = next(n for n, p in projects.items() if p == path)
        project_dependencies.append(referenced)
        E.SubElement(items, 'ProjectReference', Include=native(out / referenced / 'Build.csproj'))
    if name=='System.Text.Json':
        assert any(e['metadata'].get('PackAsAnalyzer','').lower()=='true' and e['full_path'].replace('\\','/').endswith('System.Text.Json.SourceGeneration.Roslyn4.4.csproj') for e in data['items']['ProjectReference'])
        for analyzer in sorted(generators.rglob('*.dll')):
            if analyzer.name not in {'System.Text.Json.SourceGeneration.dll','System.Text.Json.SourceGeneration.resources.dll'}:continue
            E.SubElement(items,'None',Include=native(analyzer),Pack='true',PackagePath='analyzers/dotnet/roslyn4.4/cs/'+('' if analyzer.parent==generators else analyzer.relative_to(generators).parent.as_posix()+'/'))
    resource_inputs = {}
    if resource.is_file():
        logical = 'FxResources.' + name + '.SR'
        code = ['#nullable enable', 'namespace FxResources.' + name + ' { internal static class SR {} }', 'namespace System { internal static partial class SR {', 'internal static global::System.Resources.ResourceManager ResourceManager {get;} = new global::System.Resources.ResourceManager(' + json.dumps(logical) + ', typeof(FxResources.' + name + '.SR).Assembly);']
        for e in E.parse(resource).iter('data'):
            field = e.get('name')
            assert field.isidentifier(), field
            code.append('internal static string @' + field + ' => GetResourceString(' + json.dumps(field) + ');')
        code.append('}}')
        (folder / 'SR.Generated.cs').write_text('\n'.join(code) + '\n')
        E.SubElement(items, 'Compile', Include='SR.Generated.cs')
        E.SubElement(items, 'EmbeddedResource', Include=native(resource), LogicalName=logical + '.resources')
        localizations.append(dict(assembly=name, resource=logical, culture='', strings={e.get('name'): e.findtext('value') or '' for e in E.parse(resource).iter('data')}))
        resource_inputs[resource.relative_to(source).as_posix()] = sha(resource)
        ns = {'x': 'urn:oasis:names:tc:xliff:document:1.2'}
        for xlf in sorted((resource.parent / 'xlf').glob(resource.stem + '.*.xlf')):
            parsed = E.parse(xlf)
            culture = parsed.find('x:file', ns).get('target-language')
            translations = {e.get('id'): ''.join(e.find('x:target', ns).itertext()) for e in parsed.findall('.//x:trans-unit', ns) if e.find('x:target', ns) is not None}
            localized = E.parse(resource)
            for e in localized.iter('data'):
                if e.get('name') in translations:
                    e.find('value').text = translations[e.get('name')]
            target = folder / ('Strings.' + culture + '.resx')
            localized.write(target, encoding='utf-8', xml_declaration=True)
            E.SubElement(items, 'EmbeddedResource', Include=target.name, LogicalName=logical + '.' + culture + '.resources', Culture=culture, WithCulture='true')
            localizations.append(dict(assembly=name, resource=logical, culture=culture, strings={e.get('name'): e.findtext('value') or '' for e in localized.iter('data')}))
            resource_inputs[xlf.relative_to(source).as_posix()] = sha(xlf)
    for filename in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
        E.SubElement(items, 'None', Include=native(source / filename), CopyToOutputDirectory='PreserveNewest')
    remove = E.SubElement(tree, 'Target', Name='RemoveOlderFrameworkProviders', BeforeTargets='CoreCompile')
    group = E.SubElement(remove, 'ItemGroup')
    replace = [name] + project_dependencies
    condition = "'%({kind}.FrameworkReferenceName)' == 'Microsoft.NETCore.App' And (" + ' Or '.join("'%({kind}.Filename)' == '" + value + "'" for value in replace) + ')'
    for kind in ['ReferencePath', 'ReferencePathWithRefAssemblies']:
        E.SubElement(group, kind, Remove='@(' + kind + ')', Condition=condition.format(kind=kind))
    E.SubElement(pg, 'EmitCompilerGeneratedFiles').text = 'true'
    E.SubElement(pg, 'CompilerGeneratedFilesOutputPath').text = '$(IntermediateOutputPath)generated'
    capture = E.SubElement(tree, 'Target', Name='CaptureActualGeneratorInputs', BeforeTargets='CoreCompile')
    for kind in ['Compile', 'ReferencePath', 'Analyzer']:
        E.SubElement(capture, 'WriteLinesToFile', File='$(IntermediateOutputPath)' + kind + '.txt', Lines='@(' + kind + "->'%(FullPath)')", Overwrite='true')
    E.SubElement(tree,'Import',Project=native(source/'eng/versioning.targets'))
    save(tree, folder / 'Build.csproj')
    records[name] = dict(original_project=original.relative_to(source).as_posix(), original_project_sha256=sha(original), original_cs={p.relative_to(source).as_posix(): sha(p) for p in selected}, original_resources=resource_inputs, dependencies=dependencies, project_dependencies=project_dependencies, key_policy=key_policies[name], configuration='Release', framework='net8.0', production_cs_changes=0)
(out / 'source-inputs.json').write_text(json.dumps(dict(runtime_commit='081d220c0a773ffb7c6bea6b48727833576a65ef', runtime_archive_sha256=sha(archive), source_root=native(source), projects=records, generator_manifest_sha256=sha(libs / 'NetCoreAppLibrary.props'), shared_source_policy_sha256=sha(libs / 'Directory.Build.targets'), versions_policy_sha256=sha(source / 'eng/Versions.props'), full_dependency_goal_complete=False), indent=2) + '\n')
(out / 'localization.json').write_text(json.dumps(localizations, ensure_ascii=False, indent=2) + '\n')
print('Prepared original JSON10 net8 implementations', {n: len(p['original_cs']) for n, p in records.items()}, 'resources', len(localizations), flush=True)

(out/'feed').mkdir()
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
paths=[compiler/n for n in ['CompilerHost.dll','csc.exe','Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll','System.Collections.Immutable.dll','System.Reflection.Metadata.dll']]+[generators/n for n in ['System.Text.RegularExpressions.Generator.dll','Microsoft.Interop.SourceGeneration.dll','System.Text.Json.SourceGeneration.dll']]
(out/'tool-inputs.json').write_text(json.dumps({native(p):dict(sha256=sha(p),owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip()) for p in paths},indent=2)+'\n')
