"""Prepare all declared runtime10 implementation-project evaluations."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as E

integrated = sys.argv[3:] == ['--build-targets']
assert not sys.argv[3:] or integrated, 'usage: prepare.py ARCHIVE_ROOT NEW_OUTPUT [--build-targets]'
root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
source = root / 'r'
libs = source / 'src/libraries'
native_root = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
native_out = subprocess.check_output(['cygpath', '-am', str(out)], text=True).strip()
def native(path):
    path = Path(os.path.abspath(path))
    if path.is_relative_to(out):
        return native_out + '/' + path.relative_to(out).as_posix()
    if path.is_relative_to(root):
        return native_root + '/' + path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath', '-am', str(path)], text=True).strip()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

text = (libs / 'NetCoreAppLibrary.props').read_text()
netfx = re.search(r'<NetFxReference>(.*?)</NetFxReference>', text, re.S).group(1)
names = [n.strip() for n in re.search(r'<NetCoreAppLibrary>(.*?)</NetCoreAppLibrary>', text, re.S).group(1).replace('$(NetFxReference)', netfx).split(';') if n.strip()]
projects = {}
for name in names:
    if name == 'System.Private.CoreLib':continue
    for kind, project in [('src', libs/name/'src'/(name+'.csproj')),
                          ('vb', libs/name/'src'/(name+'.vbproj')),
                          ('shim', libs/'shims'/name/'src'/(name+'.csproj'))]:
        if project.is_file():
            projects[name]=dict(kind=kind,project=project);break
    else:raise AssertionError(('Missing declared implementation project',name))

if integrated:
    for project in sorted((libs/'shims/stubs').glob('*.csproj')):
        projects['stub:'+project.stem]=dict(kind='stub',project=project)

clones = out / 'project-inputs'
clones.mkdir()
cloned = {}
original_projects = {}
def clone(path, strip_imports=False):
    path = path.resolve()
    cache_key = str(path) + str(strip_imports)
    if cache_key in cloned:
        return cloned[cache_key]
    name = hashlib.sha256(cache_key.encode()).hexdigest()[:16] + '.proj'
    target = clones / name
    cloned[cache_key] = target
    body = path.read_text(encoding='utf-8-sig')
    body = body.replace('$(MSBuildThisFileDirectory)', native(path.parent) + '/')
    body = body.replace('$(MSBuildProjectDirectory)', '$(BootstrapOriginalProjectDirectory)')
    tree = E.ElementTree(E.fromstring(body))
    tree.getroot().attrib.pop('Sdk', None)
    for parent in tree.iter():
        for item in list(parent):
            if item.tag == 'Import' and strip_imports:
                parent.remove(item)
                continue
            for attribute in ['Include', 'Update', 'Remove', 'Exclude', 'Project']:
                if attribute not in item.attrib:
                    continue
                if item.tag not in {'Compile', 'ProjectReference', 'Import', 'EmbeddedResource', 'None', 'Content', 'AdditionalFiles', 'AsnXml', 'ILLinkDescriptorsXmls', 'ILLinkSubstitutionsXmls', 'ILLinkLinkAttributesXmls', 'ILLinkDescriptorsLibraryBuildXml', 'ILLinkSuppressionsLibraryBuildXml'}:
                    continue
                value = item.get(attribute).replace('\\', '/')
                if '$(' not in value and '@(' not in value and '%(' not in value and not value.startswith('/') and not (len(value) > 1 and value[1] == ':'):
                    item.set(attribute, native(path.parent / value))
    E.indent(tree)
    tree.write(target, encoding='utf-8', xml_declaration=True)
    original_projects[path.relative_to(source).as_posix()] = sha(path)
    return target

common_props = clone(libs / 'Directory.Build.props', strip_imports=True)
common_targets = clone(libs/'Directory.Build.targets', strip_imports=True) if integrated else None
shim_props = clone(libs / 'shims/Directory.Build.props', strip_imports=True)
stub_props = clone(libs / 'shims/stubs/Directory.Build.props', strip_imports=True)
wrappers = {}
for name, entry in projects.items():
    project = entry['project']
    folder = out / 'p' / name.replace(':', '-')
    folder.mkdir(parents=True)
    wrapper = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(wrapper, 'PropertyGroup')
    values = dict(BootstrapOriginalProjectDirectory=native(project.parent), SharedOpenSourcePath=native(project.parent)+'/', TargetFramework=('net10.0-windows' if '$(NetCoreAppCurrent)-windows' in project.read_text() or entry['kind']=='shim' else 'net10.0'), ImportDirectoryBuildProps='false',
                  ImportDirectoryBuildTargets='false', EnableDefaultItems='false',
                  EnableDefaultCompileItems='false', NetCoreAppCurrent='net10.0',
                  NetCoreAppPrevious='net9.0', NetCoreAppMinimum='net8.0',
                  NetFrameworkMinimum='net462', MajorVersion='10', MinorVersion='0',
                  TargetOS='windows', TargetsWindows='true', TargetArchitecture='x64',
                  Platform='x64', Configuration='Release', RuntimeFlavor='CoreCLR',
                  IsReferenceAssemblyProject='false', IsSourceProject='true', DisableImplicitFrameworkReferences='true', CoreLibProject=native(source/'src/coreclr/System.Private.CoreLib/System.Private.CoreLib.csproj'), UriProject=native(libs/'System.Private.Uri/src/System.Private.Uri.csproj'),
                  LibrariesProjectRoot=native(libs) + '/', RepoRoot=native(source) + '/',
                  RepositoryEngineeringDir=native(source / 'eng') + '/',
                  CoreLibSharedDir=native(libs / 'System.Private.CoreLib/src') + '/')
    if integrated:
        values.update(TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',NetCoreAppCurrentVersion='10.0',TargetName=name.removeprefix('stub:'),TargetExt='.dll',DefaultLanguageSourceExtension='.vb' if entry['kind']=='vb' else '.cs',Language='VB' if entry['kind']=='vb' else 'C#',IntermediateOutputPath=native(folder/'obj')+'/',ILLinkDirectory=native(project.parent/'ILLink')+'/',AssemblyName=name.removeprefix('stub:'))
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    E.SubElement(wrapper, 'Import', Project=native(common_props))
    E.SubElement(wrapper, 'Import', Project=native(libs / 'NetCoreAppLibrary.props'))
    if entry['kind'] in {'shim', 'shimref', 'stub'}:
        E.SubElement(wrapper, 'Import', Project=native(shim_props))
    if entry['kind'] == 'stub':
        E.SubElement(wrapper, 'Import', Project=native(stub_props))
    local = project.parent.parent / 'Directory.Build.props'
    if entry['kind'] != 'stub' and local.is_file() and local not in [libs / 'Directory.Build.props', libs / 'shims/Directory.Build.props']:
        E.SubElement(wrapper, 'Import', Project=native(clone(local, strip_imports=True)))
    if entry['kind'] in {'shim', 'shimref'}:
        E.SubElement(wrapper,'PropertyGroup')

        items = E.SubElement(wrapper, 'ItemGroup')
        for path in sorted(project.parent.glob('*.cs')):
            E.SubElement(items, 'Compile', Include=native(path))
    E.SubElement(wrapper, 'Import', Project=native(clone(project)))
    if integrated:
        for file in [source/'eng/resources.targets', common_targets, source/'eng/versioning.targets', source/'eng/generators.targets', source/'eng/illink.targets']:
            E.SubElement(wrapper,'Import',Project=native(file if file==common_targets else clone(file)))
    if entry['kind'] == 'stub':
        E.SubElement(wrapper, 'Import', Project=native(clone(libs / 'shims/stubs/Directory.Build.targets', strip_imports=True)))
        pg = E.SubElement(wrapper, 'PropertyGroup')
        E.SubElement(pg, 'ForwardedTypesCompilePath').text = native(folder / (project.stem + '.ForwardedTypes.cs'))
    path = folder / project.name
    E.indent(wrapper)
    E.ElementTree(wrapper).write(path, encoding='utf-8', xml_declaration=True)
    wrappers[name] = native(path)
    entry['project'] = project.relative_to(source).as_posix()

(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
(out / 'projects.json').write_text(json.dumps(projects, indent=2) + '\n')
(out / 'source-projects.json').write_text(json.dumps(original_projects, indent=2) + '\n')
tool = out / 'evaluation-tool'
tool.mkdir()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='EvaluateImplementationProjects',
                 EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable',
                 UseAppHost='false').items():
    E.SubElement(pg, k).text = v
ig = E.SubElement(tree, 'ItemGroup')
E.SubElement(ig, 'Compile', Include=native(here / 'inputs/EvaluateProjects.cs'))
sdk = Path('/clang64/lib/dotnet/sdk/8.0.131')
for name in ['Microsoft.Build', 'Microsoft.Build.Framework', 'Microsoft.Build.Utilities.Core', 'Microsoft.NET.StringTools']:
    reference = E.SubElement(ig, 'Reference', Include=name)
    E.SubElement(reference, 'HintPath').text = native(sdk / (name + '.dll'))
E.indent(tree)
E.ElementTree(tree).write(tool / 'Build.csproj', encoding='utf-8', xml_declaration=True)
(out / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
generate = E.Element('Project')
target = E.SubElement(generate, 'Target', Name='Generate')
E.SubElement(target, 'MSBuild', Projects=';'.join(wrappers[n] for n in projects if projects[n]['kind'] == 'stub'),
             Targets='CreateCompileSourceForForwardedTypes', BuildInParallel='false')
E.ElementTree(generate).write(out / 'GenerateStubs.proj', encoding='utf-8', xml_declaration=True)
print('Prepared',len(projects),'original runtime implementation projects; full graph evaluation/build remains required')

(out/'source-roots.json').write_text(json.dumps(dict(msys_root=str(root),native_root=native_root,netcoreapp_library_props_sha256=sha(libs/'NetCoreAppLibrary.props')),indent=2)+'\n')
compiler=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')
(out/'tool-inputs.json').write_text(json.dumps({native(p):dict(sha256=sha(p),owner=subprocess.check_output(['pacman','-Qo',str(p)],text=True).strip()) for p in [compiler/'CompilerHost.dll',compiler/'csc.exe',compiler/'Microsoft.CodeAnalysis.dll',compiler/'Microsoft.CodeAnalysis.CSharp.dll',compiler/'System.Collections.Immutable.dll',compiler/'System.Reflection.Metadata.dll']},indent=2)+'\n')
