"""Build pinned upstream TDS utilities with one explicit test-stream .NET 8 fix."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

source, output = (Path(p).resolve() for p in sys.argv[1:3])
implementation = None if sys.argv[3] == '--package' else Path(sys.argv[3]).resolve()
output.mkdir()
tools = source/'src/System.Data.SqlClient/tests/Tools/TDS'
inventory = {}
for name in ('TDS', 'TDS.EndPoint', 'TDS.Servers'):
    original = tools/name/(name+'.csproj')
    upstream = E.parse(original).getroot()
    folder = output/name
    folder.mkdir()
    relative = lambda p: os.path.relpath(p, folder).replace('\\', '/')
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = E.SubElement(project, 'PropertyGroup')
    settings = dict(TargetFramework='net8.0-windows', EnableDefaultItems='false',
        ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false',
        EnableNETAnalyzers='false', NuGetAudit='false', AllowUnsafeBlocks='true',
        RootNamespace='Microsoft.SqlServer.'+name, AssemblyName='Microsoft.SqlServer.'+name,
        Nullable='disable')
    for key, value in settings.items():
        E.SubElement(props, key).text = value
    # Keep the original warning policy; add no test-specific suppressions.
    for group in upstream.findall('PropertyGroup'):
        for item in group:
            if item.tag == 'NoWarn':
                E.SubElement(props, item.tag).text = item.text
    items = E.SubElement(project, 'ItemGroup')
    sources = []
    default = upstream.findtext('./PropertyGroup/EnableDefaultCompileItems') != 'false'
    if default:
        sources.extend(sorted(original.parent.rglob('*.cs')))
    for group in upstream.findall('ItemGroup'):
        condition = group.get('Condition', '')
        assert condition in ('', "'$(TargetPlatformIdentifier)' == 'windows'", "'$(TargetPlatformIdentifier)' == 'unix'"), condition
        if condition.endswith("== 'unix'"):
            continue
        for item in group:
            if item.tag == 'Compile':
                path = item.get('Include').replace('\\', '/')
                if path.startswith('$(CommonPath)'):
                    path = source/'src/Common'/path.removeprefix('$(CommonPath)')
                else:
                    path = original.parent/path
                assert path.is_file(), path
                sources.append(path.resolve())
            elif item.tag == 'ProjectReference':
                dependency = Path(item.get('Include').replace('\\', '/')).stem
                E.SubElement(items, 'ProjectReference', Include='../'+dependency+'/build.csproj')
            else:
                # The upstream certificate is replaced by an owned ephemeral
                # certificate generated at runtime, without touching trust stores.
                assert item.tag == 'None' and item.get('Include') == 'TdsServerCertificate.pfx'
    assert len(sources) == len(set(sources)), name
    inventory[name] = {}
    for path in sorted(sources):
        inventory[name][path.relative_to(source).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        compile_path = path
        if name == 'TDS.EndPoint' and path.name == 'PlaceholderStream.cs':
            overlay = folder/'overlays'
            overlay.mkdir()
            compile_path = overlay/path.name
            compile_path.write_text(path.read_text(encoding='utf-8-sig'))
            patch = Path(__file__).resolve().with_name('0002-tds-test-peer-return-partial-handshake-reads.patch')
            subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=overlay, check=True)
            (folder/'test-stream-overlay.json').write_text(json.dumps(dict(
                original_path=path.relative_to(source).as_posix(),
                original_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
                overlay_sha256=hashlib.sha256(compile_path.read_bytes()).hexdigest()), indent=2)+'\n')
        E.SubElement(items, 'Compile', Include=relative(compile_path))
    E.indent(project)
    E.ElementTree(project).write(folder/'build.csproj', encoding='utf-8', xml_declaration=True)

project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
props = E.SubElement(project, 'PropertyGroup')
for key, value in dict(TargetFramework='net8.0-windows', OutputType='Exe', UseAppHost='false',
        EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false').items():
    E.SubElement(props, key).text = value
items = E.SubElement(project, 'ItemGroup')
E.SubElement(items, 'Compile', Include=os.path.relpath(Path(__file__).resolve().with_name('SourceSniProbe.cs'), output).replace('\\', '/'))
E.SubElement(items, 'Compile', Include=os.path.relpath(Path(__file__).resolve().with_name('MarsTdsProbe.cs'), output).replace('\\', '/'))
E.SubElement(items, 'Compile', Include=os.path.relpath(Path(__file__).resolve().with_name('MarsWindowProbe.cs'), output).replace('\\', '/'))
E.SubElement(items, 'ProjectReference', Include='TDS.Servers/build.csproj')
if implementation is None:
    E.SubElement(items, 'PackageReference', Include='System.Data.SqlClient', Version='[4.9.1]')
else:
    reference = E.SubElement(items, 'Reference', Include='System.Data.SqlClient')
    E.SubElement(reference, 'HintPath').text = os.path.relpath(implementation/'implementation/bin/Release/net8.0-windows/System.Data.SqlClient.dll', output).replace('\\', '/')
E.indent(project)
E.ElementTree(project).write(output/'Probe.csproj', encoding='utf-8', xml_declaration=True)
(output/'tds-source-inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
print('Staged complete pinned TDS utility sources, one explicit .NET 8 test-stream overlay:', {k: len(v) for k,v in inventory.items()})
