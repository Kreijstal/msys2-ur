#!/usr/bin/env python3
"""Stage Roslyn 4.9.2 compiler libraries and generators for offline .NET 8 builds."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir(parents=True)
removed = []
for path in sorted(source.rglob('*')):
    if path.is_file() and path.suffix.lower() in {'.dll', '.exe', '.pdb', '.nupkg', '.res', '.resources', '.obj', '.lib'}:
        removed.append({'path': str(path.relative_to(source)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        path.unlink()
(output / 'removed-binaries.json').write_text(json.dumps(removed, indent=2) + '\n')

common_root = Path(os.path.commonpath([source, output]))
native_root = (subprocess.check_output(['cygpath', '-m', str(common_root)], text=True).strip()
               if shutil.which('cygpath') else str(common_root))

def native(path):
    return native_root.rstrip('/') + '/' + Path(path).relative_to(common_root).as_posix()

settings = ET.parse(source / 'eng/targets/Settings.props')
key = next(e.text for e in settings.iter('MicrosoftSharedPublicKey'))
(output / 'Roslyn.public.snk').write_bytes(bytes.fromhex(key))

def write_project(folder, name, executable=False, signed=False):
    folder.mkdir(parents=True)
    project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = ET.SubElement(project, 'PropertyGroup')
    values = dict(TargetFramework='net8.0', AssemblyName=name, RootNamespace=name,
                  OutputType='Exe' if executable else 'Library', UseAppHost='false',
                  EnableDefaultItems='false', EnableNETAnalyzers='false',
                  AllowUnsafeBlocks='true', Nullable='enable', LangVersion='12.0',
                  NuGetAudit='false', Version='4.9.2', AssemblyVersion='4.9.0.0',
                  FileVersion='4.9.2.0', InformationalVersion='4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e',
                  IncludeSourceRevisionInInformationalVersion='false', ProduceReferenceAssembly='true')
    if signed:
        values.update(SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile=native(output / 'Roslyn.public.snk'))
    for k,v in values.items(): ET.SubElement(props, k).text = v
    items = ET.SubElement(project, 'ItemGroup')
    return project, props, items

def add_sources(items, folders, excluded=(), exclude_generated=False):
    for folder in folders:
        for path in sorted(folder.rglob('*.cs')):
            if path.name not in excluded and not (exclude_generated and path.relative_to(folder).parts[0] == 'Generated'):
                ET.SubElement(items, 'Compile', Include=native(path))

def save(project, folder):
    ET.indent(project)
    ET.ElementTree(project).write(folder / 'build.csproj', encoding='utf-8', xml_declaration=True)

tools = source / 'src/Tools/Source/CompilerGeneratorTools/Source'
for name in ('CSharpSyntaxGenerator', 'BoundTreeGenerator', 'CSharpErrorFactsGenerator'):
    folder = output / name
    project, props, items = write_project(folder, name, executable=True)
    add_sources(items, [tools / name], ('SourceGenerator.cs', 'CachingSourceGenerator.cs'))
    if name == 'CSharpSyntaxGenerator':
        for relative in ('CSharp/Portable/Syntax/SyntaxKind.cs', 'CSharp/Portable/Syntax/SyntaxKindFacts.cs',
                         'CSharp/Portable/Declarations/DeclarationModifiers.cs', 'Core/Portable/Symbols/WellKnownMemberNames.cs'):
            ET.SubElement(items, 'Compile', Include=native(source / 'src/Compilers' / relative))
    save(project, folder)

localizations = []

def resource(items, folder, path, classname, resource_name=None):
    namespace, _, leaf = classname.rpartition('.')
    resource_name = resource_name or classname
    lines = ['#nullable enable', f'namespace {namespace} {{ internal static class {leaf} {{',
             f'internal static System.Resources.ResourceManager ResourceManager {{ get; }} = new System.Resources.ResourceManager("{resource_name}", typeof({leaf}).Assembly);',
             'internal static System.Globalization.CultureInfo? Culture { get; set; }']
    for entry in ET.parse(path).iter('data'):
        assert not entry.get('type') and not entry.get('mimetype'), path
        name = entry.get('name')
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name), name
        lines.append(f'internal static string {name} => ResourceManager.GetString("{name}", Culture)!;')
    lines.append('}}')
    wrapper = folder / (leaf + '.g.cs')
    wrapper.write_text('\n'.join(lines) + '\n')
    ET.SubElement(items, 'Compile', Include=native(wrapper))
    ET.SubElement(items, 'EmbeddedResource', Include=native(path), LogicalName=resource_name + '.resources')
    # Preserve the 13 upstream localized satellite assemblies. XLF is text;
    # all resource binaries are produced by this build's source-built SDK.
    xlf_namespace = {'x': 'urn:oasis:names:tc:xliff:document:1.2'}
    for translation in sorted((path.parent / 'xlf').glob(path.stem + '.*.xlf')):
        xlf = ET.parse(translation)
        culture = xlf.find('x:file', xlf_namespace).get('target-language')
        translated = {}
        for unit in xlf.findall('.//x:trans-unit', xlf_namespace):
            target = unit.find('x:target', xlf_namespace)
            if target is not None:
                translated[unit.get('id')] = ''.join(target.itertext())
        localized = ET.parse(path)
        for entry in localized.iter('data'):
            if entry.get('name') in translated:
                entry.find('value').text = translated[entry.get('name')]
        translated_path = folder / (path.stem + '.' + culture + '.resx')
        localized.write(translated_path, encoding='utf-8', xml_declaration=True)
        ET.SubElement(items, 'EmbeddedResource', Include=native(translated_path),
                      LogicalName=resource_name + '.' + culture + '.resources', Culture=culture, WithCulture='true')
        localizations.append({'assembly': folder.name, 'resource': resource_name, 'culture': culture,
                              'strings': {e.get('name'): e.find('value').text or '' for e in localized.iter('data')}})

for name, pkgid in [('Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.Common'),
                    ('Microsoft.CodeAnalysis.CSharp', 'Microsoft.CodeAnalysis.CSharp')]:
    folder = output / name
    project, props, items = write_project(folder, name, signed=True)
    ET.SubElement(props, 'PackageId').text = pkgid
    ET.SubElement(props, 'PackageLicenseExpression').text = 'MIT'
    ET.SubElement(props, 'RepositoryUrl').text = 'https://github.com/dotnet/roslyn'
    ET.SubElement(props, 'RepositoryCommit').text = '9934fb9e3527e1c0c51314e57d4aab30f97e8f9e'
    ET.SubElement(props, 'PackageReadmeFile').text = 'README.md'
    ET.SubElement(items, 'None', Include=native(output / 'README.md'), Pack='true', PackagePath='/')
    if name == 'Microsoft.CodeAnalysis':
        main = source / 'src/Compilers/Core/Portable'
        ET.SubElement(props, 'DefineConstants').text = '$(DefineConstants);COMPILERCORE'
        add_sources(items, [main, source / 'src/Compilers/Core/AnalyzerDriver',
                           source / 'src/Dependencies/CodeAnalysis.Debugging',
                           source / 'src/Dependencies/PooledObjects', source / 'src/Dependencies/Collections'])
        resource(items, folder, main / 'CodeAnalysisResources.resx', 'Microsoft.CodeAnalysis.CodeAnalysisResources')
        resource(items, folder, source / 'src/Dependencies/Collections/Internal/Strings.resx',
                 'Microsoft.CodeAnalysis.Collections.Internal.SR', 'Microsoft.CodeAnalysis.Collections.Internal.Strings')
        ET.SubElement(items, 'EmbeddedResource', Include=native(main / 'Resources/default.win32manifest'),
                      LogicalName='Microsoft.CodeAnalysis.Resources.default.win32manifest')
    else:
        main = source / 'src/Compilers/CSharp/Portable'
        add_sources(items, [main, source / 'src/Compilers/CSharp/CSharpAnalyzerDriver'], exclude_generated=True)
        # Generated syntax is emitted by the upstream console generator before this build.
        ET.SubElement(items, 'Compile', Include=native(output / 'generated/*.cs'))
        resource(items, folder, main / 'CSharpResources.resx', 'Microsoft.CodeAnalysis.CSharp.CSharpResources')
        ET.SubElement(items, 'PackageReference', Include='Microsoft.CodeAnalysis.Common', Version='[4.9.2]')
    # Preserve every upstream friend declaration, using its actual public key.
    original = ET.parse(main / (name + '.csproj'))
    (output / ('api-common.txt' if name == 'Microsoft.CodeAnalysis' else 'api-csharp.txt')).write_text(
        (main / 'PublicAPI.Shipped.txt').read_text().rstrip() + '\n' +
        (main / 'PublicAPI.Unshipped.txt').read_text().rstrip() + '\n')
    declarations = []
    for friend in original.iter('InternalsVisibleTo'):
        public_key = friend.get('Key')
        if public_key:
            variable = public_key[2:-1]
            public_key = next(e.text for e in settings.iter(variable))
        else:
            public_key = key
        declarations.append('[assembly: System.Runtime.CompilerServices.InternalsVisibleTo(' +
                            json.dumps(friend.get('Include') + ', PublicKey=' + public_key) + ')]')
    attributes = folder / 'Friends.g.cs'
    if name == 'Microsoft.CodeAnalysis.CSharp':
        declarations.append('[assembly: Microsoft.CodeAnalysis.CommitHash("9934fb9e3527e1c0c51314e57d4aab30f97e8f9e")]')
    attributes.write_text('\n'.join(declarations) + '\n')
    ET.SubElement(items, 'Compile', Include=native(attributes))
    save(project, folder)
(output / 'NuGet.config').write_text('<configuration><packageSources><clear /></packageSources></configuration>\n')
(output / 'localization.json').write_text(json.dumps(localizations, ensure_ascii=False, indent=2) + '\n')
for suffix, assembly in [('common', 'Microsoft.CodeAnalysis'), ('csharp', 'Microsoft.CodeAnalysis.CSharp')]:
    (output / ('localization-' + suffix + '.json')).write_text(
        json.dumps([e for e in localizations if e['assembly'] == assembly], ensure_ascii=False, indent=2) + '\n')
