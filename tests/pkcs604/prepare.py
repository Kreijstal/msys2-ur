"""Prepare original NET6 Windows and portable Pkcs6.0.4 source profiles."""
from pathlib import Path
import copy, hashlib, json, sys, tarfile, xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:3])
out.mkdir()
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == 'b7966d5ca8035410adc673fa1f359ed973de0b70714d7db68e8172d06afc988f'
snapshot = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else out / 'snapshot'
if len(sys.argv) == 3:
    with tarfile.open(archive) as t:
        t.extractall(snapshot, filter='data')
source = snapshot / 'runtime'
manifest = json.loads((snapshot / 'source-inputs.json').read_text())
assert manifest['source_commit'] == 'e37fab9fc9f7bce120a7165491ed392a73f8ab51'
for rel, h in manifest['files'].items():
    assert sha(source / rel) == h['sha256'], rel
libs = source / 'src/libraries'
component = libs / 'System.Security.Cryptography.Pkcs'
clones = out / 'project-inputs'
clones.mkdir()
originals = {}
def clone(path, strip_imports=False):
    path = Path(path).resolve()
    dest = clones / (hashlib.sha256((native(path) + str(strip_imports)).encode()).hexdigest()[:16] + '.proj')
    if dest.exists():
        return dest
    tree = E.parse(path)
    tree.getroot().attrib.pop('Sdk', None)
    for parent in tree.iter():
        for node in list(parent):
            if strip_imports and node.tag == 'Import':
                parent.remove(node)
                continue
            for k, v in list(node.attrib.items()):
                v = v.replace('\\', '/').replace('$(MSBuildThisFileDirectory)', native(path.parent) + '/').replace('$(MSBuildProjectDirectory)', native(path.parent))
                if node.tag in {'Compile', 'ProjectReference', 'EmbeddedResource', 'AsnXml'} and k in {'Include', 'Exclude', 'Remove', 'Update'}:
                    v = ';'.join(native(path.parent / s) if s and not any(x in s for x in ['$(' , '@(', '%(']) and not Path(s).is_absolute() else s for s in v.split(';'))
                node.set(k, v)
    tree.write(dest, encoding='utf-8', xml_declaration=True)
    originals[path.relative_to(source).as_posix()] = sha(path)
    return dest

compiler_policy = E.Element('Project')
for pg in E.parse(source / 'Directory.Build.props').getroot().findall('PropertyGroup'):
    if pg.find('LangVersion') is not None:
        compiler_policy.append(copy.deepcopy(pg))
assert len(compiler_policy) == 1
E.ElementTree(compiler_policy).write(out / 'original-compiler.props', encoding='utf-8', xml_declaration=True)
shared = E.Element('Project')
for item in E.parse(libs / 'Directory.Build.targets').getroot():
    if item.tag in {'ItemGroup', 'Choose'} and any(s in E.tostring(item, encoding='unicode') for s in ['NullableAttributes.cs', 'ExceptionPolyfills.cs', 'PlatformAttributes.cs', 'System\\ObsoleteAttribute.cs', 'System\\Index.cs']):
        shared.append(copy.deepcopy(item))
E.ElementTree(shared).write(out / 'original-shared-sources.targets', encoding='utf-8', xml_declaration=True)
wrappers = {}
for label, tfm, suffix in [('windows', 'net6.0-windows', 'windows'), ('portable', 'net6.0', '')]:
    p = E.Element('Project')
    pg = E.SubElement(p, 'PropertyGroup')
    values = dict(TargetFramework=tfm, TargetFrameworkIdentifier='.NETCoreApp', TargetFrameworkVersion='v6.0',
        TargetFrameworkSuffix=suffix, TargetPlatformIdentifier='Windows' if suffix else '',
        NetCoreAppCurrent='net6.0', NetCoreAppCurrentVersion='6.0', NetCoreAppMinimum='netcoreapp3.1',
        Language='C#', IsReferenceAssembly='false', IsSourceProject='true', IsTestProject='false',
        IsTestSupportProject='false', Configuration='Release', TargetOS='windows', TargetArchitecture='x64',
        Platform='x64', AssemblyName='System.Security.Cryptography.Pkcs', RootNamespace='System.Security.Cryptography.Pkcs',
        LibrariesProjectRoot=native(libs) + '/', RepositoryEngineeringDir=native(source / 'eng') + '/',
        CoreLibSharedDir=native(libs / 'System.Private.CoreLib/src') + '/', DefaultLanguageSourceExtension='.cs')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    for path in [Path(__file__).resolve().parent / 'inputs/Arcade6.ProjectDefaults.props', source / 'eng/Versions.props', out / 'original-compiler.props', clone(libs / 'Directory.Build.props', True),
                 clone(component / 'Directory.Build.props', True), source / 'eng/targetframeworksuffix.props',
                 clone(component / 'src/System.Security.Cryptography.Pkcs.csproj'), out / 'original-shared-sources.targets']:
        E.SubElement(p, 'Import', Project=native(path))
    pg = E.SubElement(p, 'PropertyGroup')
    E.SubElement(pg, 'StringResourcesPath').text = native(component / 'src/Resources/Strings.resx')
    E.SubElement(p, 'Import', Project=native(source / 'eng/resources.targets'))
    E.SubElement(p, 'Import', Project=native(source / 'eng/versioning.targets'))
    path = out / (label + '.csproj')
    E.ElementTree(p).write(path, encoding='utf-8', xml_declaration=True)
    wrappers[label] = dict(path=native(path), framework=tfm)
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_root=native(source), source_manifest=manifest,
    original_projects_and_properties=originals, original_production_source_changes=0,
    original_profiles=['net6.0-windows', 'net6.0'], other_original_profiles_built=False,
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS prepared original Pkcs6.0.4 NET6 Windows and portable profiles')
