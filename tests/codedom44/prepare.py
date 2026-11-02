"""Prepare pinned original CodeDom 4.4 netstandard2.0 sources for the source SDK."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive, out = (Path(s).resolve() for s in sys.argv[1:])
assert not out.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
out.mkdir()
source = out / 'source'
source.mkdir()
commit = '8321c729934c0f8be754953439b88e6e1c120c24'
hashes = {}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment'] == commit
    for m in t:
        if not m.isfile():
            continue
        name = m.name.partition('/')[2]
        if not (name in {'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT', 'dir.props', 'dir.targets', 'src/dir.props', 'src/dir.targets'} or name.startswith(('src/Common/src/', 'src/System.CodeDom/'))):
            continue
        if name.lower().endswith(('.dll', '.exe', '.pdb', '.nupkg')):
            continue
        assert '..' not in Path(name).parts
        data = t.extractfile(m).read()
        assert data[:2] != b'MZ'
        p = source / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
native = lambda p: subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
here = Path(__file__).parent
key = bytes.fromhex((here / 'inputs/Open.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == 'cc7b13ffcd2ddd51'
(out / 'Open.pubkey').write_bytes(key)
original = source / 'src/System.CodeDom/src/System.CodeDom.csproj'
upstream = E.parse(original).getroot()
for node in upstream.iter():
    node.tag = node.tag.rsplit('}', 1)[-1]
for node in list(upstream):
    if node.tag == 'Import':
        upstream.remove(node)
for node in upstream.iter():
    for attr in ['Include', 'Remove', 'Update']:
        if node.get(attr):
            value = node.get(attr).replace('\\', '/')
            node.set(attr, value if value.startswith('$(CommonPath)') else native(original.parent) + '/' + value)
E.indent(upstream)
E.ElementTree(upstream).write(out / 'upstream.proj', encoding='utf-8', xml_declaration=True)
p = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(p, 'PropertyGroup')
props = dict(TargetFramework='netstandard2.0', TargetGroup='netstandard', ConfigurationGroup='Release', Platform='AnyCPU', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false', EnableDefaultItems='false', AssemblyName='System.CodeDom', RootNamespace='System.CodeDom', CommonPath=native(source / 'src/Common/src'), GenerateAssemblyInfo='false', GenerateTargetFrameworkAttribute='false', TreatWarningsAsErrors='true', WarningLevel='4', LangVersion='7.3', Nullable='disable', SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile=native(out / 'Open.pubkey'), NuGetAudit='false', UseSharedCompilation='false', EnableNETAnalyzers='false', Version='4.4.0', PackageId='System.CodeDom', RepositoryUrl='https://github.com/dotnet/corefx', RepositoryCommit=commit, PackageLicenseExpression='MIT')
for k, v in props.items():
    E.SubElement(pg, k).text = v
E.SubElement(p, 'Import', Project='upstream.proj')
E.SubElement(E.SubElement(p, 'PropertyGroup'), 'NuspecFile').text = native(out / 'System.CodeDom.nuspec')
ig = E.SubElement(p, 'ItemGroup')
for f in [native(source / 'src/Common/src/System/SR.cs'), 'SR.Generated.cs', 'AssemblyInfo.g.cs']:
    E.SubElement(ig, 'Compile', Include=f)
resource = original.parent / 'Resources/Strings.resx'
logical = 'FxResources.System.CodeDom.SR'
E.SubElement(ig, 'EmbeddedResource', Include=native(resource), LogicalName=logical + '.resources')
values = {e.get('name'): e.findtext('value') for e in E.parse(resource).findall('data')}
code = ['namespace FxResources.System.CodeDom { internal static class SR {} }', 'namespace System { internal partial class SR { private static System.Type ResourceType => typeof(' + logical + ');']
for ident in values:
    assert ident.isidentifier()
    code.append('internal static string @' + ident + ' => GetResourceString(' + json.dumps(ident) + ', null);')
code.append('}}')
(out / 'SR.Generated.cs').write_text('\n'.join(code) + '\n')
info = ['[assembly:System.Reflection.AssemblyVersion("4.0.0.0")]', '[assembly:System.Reflection.AssemblyFileVersion("4.6.25519.03")]', '[assembly:System.Reflection.AssemblyInformationalVersion("Source-built CoreFX ' + commit + '; source SDK8/csc4.4 bootstrap")]', '[assembly:System.CLSCompliant(true)]', '[assembly:System.Resources.NeutralResourcesLanguage("en-US")]']
(out / 'AssemblyInfo.g.cs').write_text('\n'.join(info) + '\n')
# Build the original separate compiler contract; its parameter names and type
# initialization metadata intentionally differ from the implementation in two entries.
reference = out / 'reference'
reference.mkdir()
rp = E.Element('Project', Sdk='Microsoft.NET.Sdk')
rpg = E.SubElement(rp, 'PropertyGroup')
for k, v in props.items():
    E.SubElement(rpg, k).text = v
E.SubElement(rpg, 'ProduceOnlyReferenceAssembly').text = 'true'
E.SubElement(rpg, 'IsPackable').text = 'false'
rig = E.SubElement(rp, 'ItemGroup')
E.SubElement(rig, 'Compile', Include=native(source / 'src/System.CodeDom/ref/System.CodeDom.cs'))
E.SubElement(rig, 'Compile', Include=native(out / 'AssemblyInfo.g.cs'))
E.indent(rp)
E.ElementTree(rp).write(reference / 'Reference.csproj', encoding='utf-8', xml_declaration=True)
E.SubElement(ig, 'None', Include=native(reference / 'bin/Release/netstandard2.0/System.CodeDom.dll'), Pack='true', PackagePath='ref/netstandard2.0/')
for lic in ['LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']:
    E.SubElement(ig, 'None', Include=native(source / lic), Pack='true', PackagePath='/')
target = E.SubElement(p, 'Target', Name='CaptureSourceInputs', BeforeTargets='CoreCompile')
for kind in ['Compile', 'ReferencePath', 'Analyzer']:
    E.SubElement(target, 'WriteLinesToFile', File='$(IntermediateOutputPath)' + kind + '.txt', Lines='@(' + kind + "->'%(FullPath)')", Overwrite='true')
E.SubElement(target, 'WriteLinesToFile', File='$(IntermediateOutputPath)policy.txt', Lines='$(TargetFramework)|$(TargetGroup)|$(DefineConstants)|$(NoWarn)|$(LangVersion)|$(TreatWarningsAsErrors)', Overwrite='true')
E.indent(p)
E.ElementTree(p).write(out / 'Library.csproj', encoding='utf-8', xml_declaration=True)
# NuGet's ref/nuspec consistency gate requires an explicit reference group.
# Supply that metadata, retaining the original empty NS2 dependency group.
package = E.Element('package')
metadata = E.SubElement(package, 'metadata')
for k, v in dict(id='System.CodeDom', version='4.4.0', authors='Microsoft; MSYS2 source bootstrap', description='Original CodeDom4.4 Standard2.0 implementation and compiler reference; source SDK8/csc4.4 bootstrap. Other historical profiles are not included.').items():
    E.SubElement(metadata, k).text = v
E.SubElement(metadata, 'license', type='expression').text = 'MIT'
E.SubElement(metadata, 'repository', type='git', url='https://github.com/dotnet/corefx', commit=commit)
E.SubElement(E.SubElement(metadata, 'dependencies'), 'group', targetFramework='.NETStandard2.0')
E.SubElement(E.SubElement(E.SubElement(metadata, 'references'), 'group', targetFramework='.NETStandard2.0'), 'reference', file='System.CodeDom.dll')
files = E.SubElement(package, 'files')
for path, target in [(out / 'bin/Release/netstandard2.0/System.CodeDom.dll', 'lib/netstandard2.0'), (reference / 'bin/Release/netstandard2.0/System.CodeDom.dll', 'ref/netstandard2.0'), (source / 'LICENSE.TXT', ''), (source / 'THIRD-PARTY-NOTICES.TXT', '')]:
    E.SubElement(files, 'file', src=native(path), target=target)
E.indent(package)
E.ElementTree(package).write(out / 'System.CodeDom.nuspec', encoding='utf-8', xml_declaration=True)
(out / 'feed').mkdir()
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed" value="' + native(Path('/clang64/lib/dotnet/library-packs')) + '"/></packageSources></configuration>\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_commit=commit, source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), original_file_sha256=hashes, resources=values, production_CSharp_changes=0, compiled_profile='netstandard2.0', original_buildtools_host_replayed=False, other_original_profiles_built=False), indent=2) + '\n')
print('PASS prepared original CodeDom4.4 NS2 sources')
