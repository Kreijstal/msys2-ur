"""Prepare a package-local Compiler5 host and original supported runtime9 libraries."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
def native(p):
    return subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
out_native = native(out)
source = out / 'runtime-source'
extract = '''import pathlib,sys,tarfile,hashlib,json
archive,output=sys.argv[1:];source=pathlib.Path(output);source.mkdir();removed=[]
with tarfile.open(archive) as tar:
 assert tar.pax_headers['comment']=='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3'
 for item in tar:
  if not item.isfile():continue
  name=item.name.partition('/')[2];p=pathlib.PurePosixPath(name)
  assert name and '..' not in p.parts and not p.is_absolute()
  data=tar.extractfile(item).read()
  if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip','.mdb'} or data[:2]==b'MZ':
   removed.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest()));continue
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
(source.parent/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\\n')
'''
subprocess.run(['/clang64/bin/python.exe', '-c', extract, native(archive), native(source)], check=True)
def fast_native(p):
    return out_native + '/' + p.resolve().relative_to(out).as_posix()
def posix(p):
    p = p.replace('\\', '/')
    assert p.lower().startswith(out_native.lower() + '/'), p
    return out / p[len(out_native) + 1:]
def save(tree, path):
    E.indent(tree)
    E.ElementTree(tree).write(path, encoding='utf-8', xml_declaration=True)
def project(name, assembly, exe=False, compiler=None):
    folder = out / name
    folder.mkdir()
    tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(tree, 'PropertyGroup')
    values = dict(TargetFramework='net8.0', AssemblyName=assembly, OutputType='Exe' if exe else 'Library', UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', LangVersion='preview', AllowUnsafeBlocks='true', UseSharedCompilation='false', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false')
    values.update(CscToolPath=native(compiler or Path('/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2')), CscToolExe='csc49.cmd' if compiler is None else 'csc50-build.cmd')
    for k, v in values.items():
        E.SubElement(pg, k).text = v
    return folder, tree, pg, E.SubElement(tree, 'ItemGroup')
bootstrap = Path('/clang64/lib/dotnet-bootstrap/roslyn-5.0.0')
owner = subprocess.check_output(['pacman', '-Qo', str(bootstrap / 'csc.exe')], text=True).strip()
assert 'mingw-w64-clang-x86_64-dotnet-bootstrap-tools' in owner
compiler = out / 'compiler'
shutil.copytree(bootstrap, compiler)
baseline = {p.relative_to(bootstrap).as_posix(): sha(p) for p in bootstrap.rglob('*') if p.is_file()}
(compiler / 'csc50-build.cmd').write_text('@echo off\r\n"' + native(Path('/clang64/lib/dotnet/dotnet.exe')) + '" "' + fast_native(compiler / 'CompilerHost.dll') + '" %*\r\nexit /b %errorlevel%\r\n')
folder, tree, pg, items = project('host', 'CompilerHost', True)
E.SubElement(items, 'Compile', Include=native(here / 'inputs/CompilerHost.cs'))
E.SubElement(pg, 'OutputPath').text = fast_native(compiler)
E.SubElement(pg, 'AppendTargetFrameworkToOutputPath').text = 'false'
save(tree, folder / 'Build.csproj')
config = E.Element('configuration')
E.SubElement(E.SubElement(config, 'packageSources'), 'clear')
save(config, out / 'NuGet.config')
folder, tree, pg, items = project('evaluate-tool', 'EvaluateRuntimeProjects', True)
E.SubElement(items, 'Compile', Include=native(here / 'inputs/EvaluateProjects.cs'))
sdk = Path('/clang64/lib/dotnet/sdk/8.0.131')
for name in ['Microsoft.Build', 'Microsoft.Build.Framework', 'Microsoft.Build.Utilities.Core', 'Microsoft.NET.StringTools']:
    E.SubElement(E.SubElement(items, 'Reference', Include=name), 'HintPath').text = native(sdk / (name + '.dll'))
save(tree, folder / 'Build.csproj')
env = dict(os.environ, DOTNET_CLI_HOME=fast_native(out / 'cli-home'), NUGET_PACKAGES=fast_native(out / 'cache'), DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
for name in ['host', 'evaluate-tool']:
    with (out / (name + '-build.log')).open('w') as log:
        subprocess.run([dotnet, 'build', fast_native(out / name / 'Build.csproj'), '-c', 'Release', '--configfile', fast_native(out / 'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
libs = source / 'src/libraries'
wrappers = {}
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']:
    original = libs / name / 'src' / (name + '.csproj')
    folder = out / 'evaluation' / name
    folder.mkdir(parents=True)
    tree = E.fromstring(original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)', fast_native(original.parent) + '/'))
    tree.attrib.pop('Sdk')
    for item in tree.iter('Compile'):
        value = item.get('Include', '').replace('\\', '/')
        if value and '$(' not in value:
            item.set('Include', fast_native(original.parent / value))
    save(tree, folder / 'upstream.proj')
    wrapper = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(wrapper, 'PropertyGroup')
    for k, v in dict(Configuration='Release', TargetFramework='net8.0', TargetFrameworkIdentifier='.NETCoreApp', ImportDirectoryBuildProps='false', ImportDirectoryBuildTargets='false', EnableDefaultItems='false', NetCoreAppCurrent='net9.0', NetCoreAppPrevious='net8.0', NetCoreAppMinimum='net8.0', NetFrameworkMinimum='net462', TargetOS='windows', TargetsWindows='true', CommonPath=fast_native(libs / 'Common/src') + '/', CoreLibSharedDir=fast_native(libs / 'System.Private.CoreLib/src') + '/', LibrariesProjectRoot=fast_native(libs) + '/').items():
        E.SubElement(pg, k).text = v
    E.SubElement(wrapper, 'Import', Project='upstream.proj')
    path = folder / 'Evaluate.csproj'
    save(wrapper, path)
    wrappers[name] = fast_native(path)
(out / 'wrappers.json').write_text(json.dumps(wrappers, indent=2) + '\n')
env.update(MSBuildSDKsPath=native(sdk / 'Sdks'), MSBUILD_EXE_PATH=native(sdk / 'MSBuild.dll'))
with (out / 'evaluation.log').open('w') as log:
    subprocess.run([dotnet, fast_native(out / 'evaluate-tool/bin/Release/net8.0/EvaluateRuntimeProjects.dll'), fast_native(out / 'wrappers.json'), fast_native(out / 'evaluated.json')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
evaluated = json.loads((out / 'evaluated.json').read_text())
key = bytes.fromhex((here / 'inputs/Microsoft.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
(out / 'Microsoft.pubkey').write_bytes(key)
records, resources = {}, []
for name in ['System.Collections.Immutable', 'System.Reflection.Metadata']:
    original = libs / name / 'src' / (name + '.csproj')
    folder, tree, pg, items = project(name, name, compiler=compiler)
    data = evaluated[name]
    assert 'DEBUG' not in data['properties']['DefineConstants'].split(';')
    for k, v in dict(Version='9.0.0', AssemblyVersion='9.0.0.0', FileVersion='9.0.0.0', InformationalVersion='9.0.0+9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3', IncludeSourceRevisionInInformationalVersion='false', SignAssembly='true', PublicSign='true', AssemblyOriginatorKeyFile=fast_native(out / 'Microsoft.pubkey'), DefineConstants=data['properties']['DefineConstants']).items():
        E.SubElement(pg, k).text = v
    files = [posix(e['full_path']) for e in data['items']['Compile']]
    resx = original.parent / 'Resources/Strings.resx'
    files.append(libs / 'Common/src/System/SR.cs')
    assert len(files) == len(set(files)) and all(p.is_file() for p in files)
    for p in files:
        E.SubElement(items, 'Compile', Include=fast_native(p))
    for reference in data['items']['ProjectReference']:
        ident = Path(reference['full_path'].replace('\\', '/')).stem
        assert ident == 'System.Collections.Immutable', (name, ident)
        E.SubElement(items, 'ProjectReference', Include=fast_native(out / ident / 'Build.csproj'))
    remove = E.SubElement(tree, 'Target', Name='RemoveFrameworkSelfReference', BeforeTargets='CoreCompile')
    group = E.SubElement(remove, 'ItemGroup')
    replacements = [name] + (['System.Collections.Immutable'] if name == 'System.Reflection.Metadata' else [])
    for kind in ['ReferencePath', 'ReferencePathWithRefAssemblies']:
        condition = "'%({kind}.FrameworkReferenceName)' == 'Microsoft.NETCore.App' And (" + ' Or '.join("'%({kind}.Filename)' == '" + value + "'" for value in replacements) + ')'
        E.SubElement(group, kind, Remove='@(' + kind + ')', Condition=condition.format(kind=kind))
    logical = 'FxResources.' + name + '.SR'
    code = ['#nullable enable', 'namespace FxResources.' + name + ' { internal static class SR {} }', 'namespace System { internal static partial class SR {', 'internal static global::System.Resources.ResourceManager ResourceManager {get;} = new global::System.Resources.ResourceManager(' + json.dumps(logical) + ',typeof(FxResources.' + name + '.SR).Assembly);']
    strings = {}
    for e in E.parse(resx).iter('data'):
        field = e.get('name')
        assert field.isidentifier()
        strings[field] = e.findtext('value') or ''
        code.append('internal static string @' + field + ' => GetResourceString(' + json.dumps(field) + ');')
    code.append('}}')
    (folder / 'SR.Generated.cs').write_text('\n'.join(code) + '\n')
    E.SubElement(items, 'Compile', Include='SR.Generated.cs')
    E.SubElement(items, 'EmbeddedResource', Include=fast_native(resx), LogicalName=logical + '.resources')
    capture = E.SubElement(tree, 'Target', Name='CaptureCompilerInputs', BeforeTargets='CoreCompile')
    for kind in ['Compile', 'ReferencePath']:
        E.SubElement(capture, 'WriteLinesToFile', File='$(IntermediateOutputPath)' + kind + '.txt', Lines='@(' + kind + "->'%(FullPath)')", Overwrite='true')
    save(tree, folder / 'Build.csproj')
    records[name] = dict(original_project=original.relative_to(source).as_posix(), original_project_sha256=sha(original), original_cs={p.relative_to(source).as_posix(): sha(p) for p in files}, original_resx={resx.relative_to(source).as_posix(): sha(resx)}, configuration='Release', production_source_changes=0)
    resources.append(dict(assembly=name, resource=logical, strings=strings))
(out / 'resources.json').write_text(json.dumps(resources, ensure_ascii=False, indent=2) + '\n')
(out / 'source-inputs.json').write_text(json.dumps(dict(runtime_commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3', runtime_archive_sha256=sha(archive), installed_compiler_owner=owner, installed_compiler_files_sha256=baseline, compiler_host_source_sha256=sha(here / 'inputs/CompilerHost.cs'), projects=records, full_dependency_goal_complete=False), indent=2) + '\n')
print('Prepared source Compiler5 package host and runtime9:', {n: len(r['original_cs']) for n, r in records.items()}, flush=True)
