"""Prepare the unchanged original ASN.1 8.0.1 NET8 project and compiler policy."""
from pathlib import Path
import copy, hashlib, json, sys, tarfile, zipfile, xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:3])
out.mkdir()
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == 'f688556c4895b4e484b0a17d0291947a6d6dfc7dc482dcbda3d4368399ab9f05'
documentation_archive = Path(sys.argv[3]).resolve()
assert sha(documentation_archive) == '48b7ad1dedcdcd36143c1b8611f6f8d185024b253781695b0afb06133449139a'
snapshot = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else out / 'snapshot'
if len(sys.argv) == 4:
    with tarfile.open(archive) as t:
        t.extractall(snapshot, filter='data')
source = snapshot / 'runtime'
manifest = json.loads((snapshot / 'source-inputs.json').read_text())
doc_version = E.parse(source / 'eng/Versions.props').findtext('.//MicrosoftPrivateIntellisenseVersion')
assert doc_version == '8.0.0-preview-20230918.1'
doc_member = 'IntellisenseFiles/net/1033/System.Formats.Asn1.xml'
documentation = out / 'documentation-cache/microsoft.private.intellisense' / doc_version / doc_member
documentation.parent.mkdir(parents=True)
with zipfile.ZipFile(documentation_archive) as z:
    documentation.write_bytes(z.read(doc_member))
assert manifest['source_commit'] == '2aade6beb02ea367fd97c4070a4198802fe61c03'
for rel, h in manifest['files'].items():
    assert sha(source / rel) == h['sha256'], rel
libs = source / 'src/libraries'
component = libs / 'System.Formats.Asn1'
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
pre_arcade = E.Element('Project')
for item in E.parse(libs / 'Directory.Build.props').getroot():
    if item.tag == 'Import':
        break
    pre_arcade.append(copy.deepcopy(item))
E.ElementTree(pre_arcade).write(out / 'original-pre-arcade.props', encoding='utf-8', xml_declaration=True)
shared = E.Element('Project')
for item in E.parse(libs / 'Directory.Build.targets').getroot():
    if item.tag in {'ItemGroup', 'Choose'} and any(s in E.tostring(item, encoding='unicode') for s in ['NullableAttributes.cs', 'ExceptionPolyfills.cs', 'PlatformAttributes.cs', 'System\\ObsoleteAttribute.cs', 'System\\Index.cs']):
        shared.append(copy.deepcopy(item))
E.ElementTree(shared).write(out / 'original-shared-sources.targets', encoding='utf-8', xml_declaration=True)
wrappers = {}
for label, tfm, suffix in [('System.Formats.Asn1', 'net8.0', '')]:
    p = E.Element('Project')
    pg = E.SubElement(p, 'PropertyGroup')
    values = dict(TargetFramework=tfm, TargetFrameworkIdentifier='.NETCoreApp', TargetFrameworkVersion='v8.0',
        TargetFrameworkSuffix=suffix, TargetPlatformIdentifier='Windows' if suffix else '',
        NetCoreAppCurrent='net8.0', NetCoreAppCurrentVersion='8.0', NetCoreAppPrevious='net7.0', NetCoreAppMinimum='net6.0', NetFrameworkMinimum='net462', OfficialBuild='true',
        Language='C#', IsReferenceAssembly='false', IsSourceProject='true', IsTestProject='false',
        IsTestSupportProject='false', Configuration='Release', TargetOS='windows', TargetArchitecture='x64',
        Platform='x64', AssemblyName='System.Formats.Asn1', RootNamespace='System.Formats.Asn1',
        LibrariesProjectRoot=native(libs) + '/', RepositoryEngineeringDir=native(source / 'eng') + '/',
        NuGetPackageRoot=native(out / 'documentation-cache') + '/',
        CoreLibSharedDir=native(libs / 'System.Private.CoreLib/src') + '/', DefaultLanguageSourceExtension='.cs')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    for path in [out / 'original-pre-arcade.props', Path(__file__).resolve().parent / 'inputs/Arcade8.ProjectDefaults.props', source / 'eng/Versions.props', out / 'original-compiler.props',
                 clone(libs / 'Directory.Build.props', True), clone(component / 'src/System.Formats.Asn1.csproj'), out / 'original-shared-sources.targets']:
        E.SubElement(p, 'Import', Project=native(path))
    pg = E.SubElement(p, 'PropertyGroup')
    E.SubElement(pg, 'StringResourcesPath').text = native(component / 'src/Resources/Strings.resx')
    E.SubElement(p, 'Import', Project=native(source / 'eng/resources.targets'))
    E.SubElement(p, 'Import', Project=native(source / 'eng/versioning.targets'))
    E.SubElement(p, 'Import', Project=native(source / 'eng/intellisense.targets'))
    path = out / (label + '.csproj')
    E.ElementTree(p).write(path, encoding='utf-8', xml_declaration=True)
    wrappers[label] = dict(path=native(path), framework=tfm)
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_root=native(source), source_manifest=manifest,
    original_projects_and_properties=originals, original_production_source_changes=0,
    original_profiles=['net8.0'], other_original_profiles_built=False,
    original_documentation=dict(archive_sha256=sha(documentation_archive), version=doc_version,
        member=doc_member, sha256=sha(documentation), extracted_path=native(documentation)),
    full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS prepared original ASN.1 8.0.1 NET8 profile')
