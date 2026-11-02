"""Prepare the original declared NET6 core contract graph without changing source TFMs."""
from pathlib import Path
import copy, hashlib, json, re, sys, tarfile, xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native = lambda p: Path(p).resolve().as_posix()
assert sha(archive) == '45e8453e4868b201f8dda3214931cce9ebfd965272c8e7972e49c56291d05106'
with tarfile.open(archive) as t:
    t.extractall(out / 'snapshot', filter='data')
source = out / 'snapshot/runtime'
manifest = json.loads((out / 'snapshot/source-inputs.json').read_text())
for rel, h in manifest['files'].items():
    assert sha(source / rel) == h, rel
libs = source / 'src/libraries'
group = E.parse(libs / 'NetCoreAppLibrary.props').findtext('.//NetCoreAppLibrary')
names = [s.strip() for s in group.split(';') if s.strip()]
private = [n for n in names if n.startswith('System.Private.')]
public = [n for n in names if n not in private]
assert len(names) == 142 and len(public) == 137
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
            for key, value in list(node.attrib.items()):
                value = value.replace('\\', '/').replace('$(MSBuildThisFileDirectory)', native(path.parent) + '/').replace('$(MSBuildProjectDirectory)', native(path.parent))
                if node.tag in {'Compile', 'ProjectReference', 'EmbeddedResource', 'Import'} and key in {'Include', 'Exclude', 'Remove', 'Update', 'Project'}:
                    parts = []
                    for part in value.split(';'):
                        if part and not any(c in part for c in ['$(' , '@(', '%(']) and not Path(part).is_absolute():
                            part = native(path.parent / part)
                        parts.append(part)
                    value = ';'.join(parts)
                node.set(key, value)
    tree.write(dest, encoding='utf-8', xml_declaration=True)
    originals[path.relative_to(source).as_posix()] = sha(path)
    return dest

compiler_policy = E.Element('Project')
for pg in E.parse(source / 'Directory.Build.props').getroot().findall('PropertyGroup'):
    if pg.find('LangVersion') is not None:
        compiler_policy.append(copy.deepcopy(pg))
assert len(compiler_policy) == 1
E.ElementTree(compiler_policy).write(out / 'original-compiler.props', encoding='utf-8', xml_declaration=True)
common = clone(libs / 'Directory.Build.props', True)
wrappers = {}
projects = {}
for name in public:
    original = libs / name / 'ref' / (name + '.csproj')
    assert original.is_file(), name
    folder = out / 'p' / name
    folder.mkdir(parents=True)
    wrapper = E.Element('Project')
    pg = E.SubElement(wrapper, 'PropertyGroup')
    values = dict(TargetFramework='net6.0', TargetFrameworkIdentifier='.NETCoreApp', TargetFrameworkVersion='v6.0',
        NetCoreAppCurrent='net6.0', NetCoreAppCurrentVersion='6.0', NetCoreAppMinimum='netcoreapp3.1',
        NetFrameworkToolCurrent='net472', Language='C#', IsReferenceAssembly='true', IsSourceProject='false',
        IsTestProject='false', IsTestSupportProject='false', Configuration='Release', TargetOS='windows',
        TargetsWindows='true', TargetsAnyOS='true', TargetArchitecture='x64', Platform='x64',
        AssemblyName=name, RootNamespace=name, LibrariesProjectRoot=native(libs) + '/', RepoRoot=native(source) + '/',
        RepositoryEngineeringDir=native(source / 'eng') + '/', CoreLibSharedDir=native(libs / 'System.Private.CoreLib/src') + '/')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    E.SubElement(wrapper, 'Import', Project=native(source / 'eng/Versions.props'))
    E.SubElement(wrapper, 'Import', Project=native(out / 'original-compiler.props'))
    E.SubElement(wrapper, 'Import', Project=native(common))
    E.SubElement(wrapper, 'Import', Project=native(libs / 'NetCoreAppLibrary.props'))
    E.SubElement(wrapper, 'Import', Project=native(source / 'eng/referenceAssemblies.props'))
    local = original.parent.parent / 'Directory.Build.props'
    if local.is_file():
        E.SubElement(wrapper, 'Import', Project=native(clone(local, True)))
    E.SubElement(wrapper, 'Import', Project=native(clone(original)))
    E.SubElement(wrapper, 'Import', Project=native(source / 'eng/versioning.targets'))
    path = folder / (name + '.csproj')
    E.ElementTree(wrapper).write(path, encoding='utf-8', xml_declaration=True)
    wrappers[name] = native(path)
    projects[name] = dict(project=original.relative_to(source).as_posix(), framework='net6.0')
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
(out / 'projects.json').write_text(json.dumps(projects, indent=2) + '\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(source_root=native(source), source_manifest=manifest,
    original_projects_and_properties=originals, declared_runtime_assemblies=names, private_implementations_excluded=private,
    public_core_contracts=public, compatibility_facades_built=False, full_targeting_pack_built=False,
    original_production_source_changes=0, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS prepared all 137 original NET6 core contract projects; compatibility facades remain separate')
