"""Stage the exact SqlClient sources without prebuilt implementation inputs.

The default compile prototype retains upstream's native SNI selection. The
explicit --managed-sni candidate applies four source patches; its runtime parity
and complete packaging remain unverified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--managed-sni', action='store_true',
                    help='Apply the explicit Windows managed networking source port in Release and Debug')
args = parser.parse_args()
source, output = args.source.resolve(), args.output.resolve()
output.mkdir()
inputs = Path(__file__).resolve().parent
removed = []
for path in sorted(source.rglob('*')):
    if path.is_file() and path.suffix.lower() in {'.dll', '.exe', '.nupkg', '.pdb', '.so', '.dylib', '.a', '.lib', '.winmd', '.res'}:
        removed.append({'path': str(path.relative_to(source)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        path.unlink()
(output/'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
key = bytes.fromhex((inputs/'Microsoft.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
(output/'Microsoft.public.snk').write_bytes(key)
original = source/'src/System.Data.SqlClient/src/System.Data.SqlClient.csproj'
factory = original.parent/'System/Data/SqlClient/TdsParserStateObjectFactory.Windows.cs'
if args.managed_sni:
    overlay = output/'overlays'
    overlay.mkdir()
    # Preserve the pinned original source tree and retain a reviewable patch.
    port_inputs = [(factory, inputs/'0001-use-managed-sni-on-windows.patch'),
        (source/'src/Common/src/Interop/Windows/SspiCli/SecuritySafeHandles.cs',
         inputs/'0003-pass-complete-spns-to-windows-sspi.patch'),
        (original.parent/'System/Data/SqlClient/SNI/SNIProxy.cs',
         inputs/'0004-accept-short-custom-named-pipe-paths.patch'),
        (original.parent/'System/Data/SqlClient/SNI/SNIMarsHandle.cs',
         inputs/'0005-honor-inclusive-smp-send-window.patch')]
    port_overlays = []
    for path, patch in port_inputs:
        staged = overlay/path.name
        staged.write_text(path.read_text(encoding='utf-8-sig'))
        subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=overlay, check=True)
        port_overlays.append(dict(original_path=path.relative_to(source).as_posix(),
            original_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            patch_name=patch.name, patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
            overlay_sha256=hashlib.sha256(staged.read_bytes()).hexdigest()))
    (output/'managed-sni-port.json').write_text(json.dumps(dict(overlays=port_overlays,
        release_and_debug_use_managed_sni=True,
        complete_runtime_compatibility_verified=False), indent=2)+'\n')
for role, framework in [('implementation', 'net8.0-windows'), ('contract', 'net8.0')]:
    folder = output/role
    folder.mkdir()
    relative = lambda p: os.path.relpath(p, folder).replace('\\', '/')
    upstream = E.parse(original).getroot()
    upstream.attrib.pop('Sdk')
    assert upstream.findtext('./PropertyGroup/AssemblyVersion') == '4.6.1.6'
    for group in upstream.findall('PropertyGroup'):
        for prop in list(group):
            if prop.tag in {'TargetFrameworks', 'TargetFramework'}:
                group.remove(prop)
    for group in upstream.findall('ItemGroup'):
        for item in list(group):
            if item.tag == 'PackageReference':
                assert item.get('Include') == 'runtime.native.System.Data.SqlClient.sni'
                group.remove(item)
                continue
            for attribute in ['Include', 'Remove', 'Update']:
                value = item.get(attribute)
                if value and not value.startswith(('$(', '@(')):
                    item.set(attribute, relative(original.parent)+'/'+value.replace('\\', '/'))
    for imp in upstream.findall('Import'):
        assert imp.get('Project') == 'GenerateThisAssemblyCs.targets'
        shutil.copyfile(original.parent/imp.get('Project'), folder/imp.get('Project'))
    E.indent(upstream)
    E.ElementTree(upstream).write(folder/'upstream.proj', encoding='utf-8', xml_declaration=True)
    project = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = E.SubElement(project, 'PropertyGroup')
    values = dict(TargetFramework=framework, TargetFrameworkIdentifier='.NETCoreApp',
        NetCurrent='net8.0', NetMinimum='net6.0', NetFrameworkMinimum='net462',
        CommonPath=relative(source/'src/Common')+'/',
        EnableDefaultItems='false', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false',
        AssemblyName='System.Data.SqlClient', RootNamespace='System.Data.SqlClient',
        Version='4.9.1', FileVersion='4.9.1.0',
        InformationalVersion='4.9.1+84b081710c66cc560b77d4de38cee493c3a38e9d',
        IncludeSourceRevisionInInformationalVersion='false', EnableNETAnalyzers='false', NuGetAudit='false',
        SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile='../Microsoft.public.snk',
        Nullable='disable', ProduceReferenceAssembly='true', DefineConstants='$(DefineConstants);netcoreapp',
        NoWarn='CS0436;CS0618;CS0649;SYSLIB0051;SYSLIB0004')
    for name, value in values.items():
        E.SubElement(props, name).text = value
    E.SubElement(project, 'Import', Project='upstream.proj')
    items = E.SubElement(project, 'ItemGroup')
    if args.managed_sni and role == 'implementation':
        for path, _ in port_inputs:
            E.SubElement(items, 'Compile', Remove=relative(path))
            E.SubElement(items, 'Compile', Include=relative(overlay/path.name))
    E.SubElement(items, 'Compile', Include=relative(source/'src/Common/src/System/SR.cs'))
    E.SubElement(items, 'Compile', Include='SR.Generated.cs')
    resource = original.parent/'Resources/Strings.resx'
    logical = 'FxResources.System.Data.SqlClient.SR'
    E.SubElement(items, 'EmbeddedResource', Include=relative(resource), LogicalName=logical+'.resources')
    code = ['namespace System { internal static partial class SR {',
            'private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager('+json.dumps(logical)+', typeof(SR).Assembly);']
    for entry in E.parse(resource).iter('data'):
        name = entry.get('name')
        assert name.isidentifier(), name
        code.append('internal static string '+name+' => GetResourceString('+json.dumps(name)+');')
    code.append('}}')
    (folder/'SR.Generated.cs').write_text('\n'.join(code)+'\n')
    target = E.SubElement(project, 'Target', Name='RecordSourceSniCompileInputs', AfterTargets='CoreCompile')
    for kind, filename in [('Compile','compile-inputs.txt'),('ReferencePath','reference-inputs.txt'),('EmbeddedResource','resource-inputs.txt')]:
        E.SubElement(target, 'WriteLinesToFile', File=filename,
            Lines='@('+kind+"->'%(FullPath)')", Overwrite='true', Encoding='UTF-8')
    E.indent(project)
    E.ElementTree(project).write(folder/'build.csproj', encoding='utf-8', xml_declaration=True)
(output/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
