"""Build the original CoreFX netstandard-Windows_NT ProtectedData configuration."""
from pathlib import Path
import copy, hashlib, json, os, subprocess, sys, tarfile
import xml.etree.ElementTree as E

archive, out = (Path(p).resolve() for p in sys.argv[1:3])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == 'c69ee661412027223f5236819e653bf2d0a7d593a7e487f78d34616ec52bbf99'
snapshot = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else out / 'snapshot'
if len(sys.argv) == 3:
    with tarfile.open(archive) as t:
        t.extractall(snapshot, filter='data')
source = snapshot / 'corefx'
manifest = json.loads((snapshot / 'source-inputs.json').read_text())
assert manifest['source_commit'] == '8321c729934c0f8be754953439b88e6e1c120c24'
for rel, expected in manifest['files'].items():
    assert sha(source / rel) == expected, rel
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
sdk = host8.parent / 'sdk/8.0.131'
compiler = host8.parent / 'compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((host8.parent / 'packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
env = dict(os.environ, DOTNET_ROOT=native(host8.parent), DOTNET_ROOT_X64=native(host8.parent),
           MSBuildEnableWorkloadResolver='false', DOTNET_CLI_TELEMETRY_OPTOUT='1',
           DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'empty-cache'))
commands = []

def run(label, cmd, runtime=host8):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                           env=env | dict(DOTNET_ROOT=native(runtime.parent), DOTNET_ROOT_X64=native(runtime.parent)), timeout=240)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)

helper = here / 'buildtools-resource-helper'
helper_manifest = json.loads((helper / 'source-inputs.json').read_text())
for rel, expected in helper_manifest['files'].items():
    assert sha(helper / rel) == expected, rel
assert '<CLSCompliant Condition="\'$(CLSCompliant)\'==\'\'">true</CLSCompliant>' in (helper / 'Build.Common.targets').read_text()
tools = out / 'tools'
tools.mkdir()
p = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(p, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', AssemblyName='Microsoft.DotNet.Build.Tasks', EnableDefaultItems='false',
                 EnableNETAnalyzers='false', NuGetAudit='false').items():
    E.SubElement(pg, k).text = v
ig = E.SubElement(p, 'ItemGroup')
for name in ['GenerateResourcesCode.cs', 'GenerateCurrentVersion.cs']:
    E.SubElement(ig, 'Compile', Include=native(helper / name))
E.SubElement(ig, 'Compile', Include=native(here / 'CheckReleaseVersion.cs'))
for name in ['Microsoft.Build.Framework', 'Microsoft.Build.Utilities.Core']:
    E.SubElement(E.SubElement(ig, 'Reference', Include=name), 'HintPath').text = native(sdk / (name + '.dll'))
E.ElementTree(p).write(tools / 'Tasks.csproj', encoding='utf-8', xml_declaration=True)
(tools / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
run('tools', [host8, 'build', tools / 'Tasks.csproj', '-c', 'Release', '--configfile', tools / 'NuGet.config',
              '-p:UseSharedCompilation=false', '-v:minimal'])

name = 'System.Security.Cryptography.ProtectedData'
component = source / 'src' / name
original = component / 'src' / (name + '.csproj')
ns = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}
policy = E.parse(component / 'dir.props')
assert policy.findtext('.//m:AssemblyVersion', namespaces=ns) == '4.0.2.0'
assert policy.findtext('.//m:AssemblyKey', namespaces=ns) == 'MSFT'
root_policy = E.parse(source / 'dir.props')
assert root_policy.findtext('.//m:GenerateTargetFrameworkAttribute', namespaces=ns) == 'false'
assert 'netstandard-Windows_NT;' in E.parse(component / 'src/Configurations.props').findtext('.//m:BuildConfigurations', namespaces=ns)

# Keep all original project item groups and conditions; replace the unavailable repository-wide imports.
upstream = copy.deepcopy(E.parse(original).getroot())
for node in list(upstream):
    if node.tag.rsplit('}', 1)[-1] == 'Import':
        upstream.remove(node)
for node in upstream.iter():
    node.tag = node.tag.rsplit('}', 1)[-1]
    for key, value in list(node.attrib.items()):
        value = value.replace('\\', '/')
        if node.tag == 'Compile' and key == 'Include' and '$(' not in value:
            value = native(original.parent / value)
        node.set(key, value)
E.ElementTree(upstream).write(out / 'upstream.proj', encoding='utf-8', xml_declaration=True)
p = E.Element('Project')
pg = E.SubElement(p, 'PropertyGroup')
values = dict(TargetGroup='netstandard', OSGroup='Windows_NT', TargetsWindows='true', ConfigurationGroup='Release',
              TargetFramework='netstandard2.0', AssemblyName=name, CommonPath=native(source / 'src/Common/src'),
              GenerateTargetFrameworkAttribute='false', AssemblyVersion='4.0.2.0', MajorVersion='4', MinorVersion='6',
              BuildNumberMajor='25519', BuildNumberMinor='03', LatestCommit=manifest['source_commit'] + '+msys2-empty-input-backport',
              BuildToolsTaskDir=native(tools / 'bin/Release/net8.0') + '/',
              IntermediateOutputPath=native(out / 'generated') + '/',
              StringResourcesPath=native(component / 'src/Resources/Strings.resx'),
              WarningLevel='4', TreatWarningsAsErrors='true', CLSCompliant='true', IsDotNetFrameworkProductAssembly='true')
for k, v in values.items():
    E.SubElement(pg, k).text = v
(out / 'generated').mkdir()
E.SubElement(p, 'Import', Project=native(out / 'upstream.proj'))
E.SubElement(p, 'Import', Project=native(helper / 'resources.targets'))
E.SubElement(p, 'Import', Project=native(helper / 'versioning.targets'))
E.SubElement(p, 'UsingTask', TaskName='CheckReleaseVersion', AssemblyFile=native(tools / 'bin/Release/net8.0/Microsoft.DotNet.Build.Tasks.dll'))
E.SubElement(p, 'UsingTask', TaskName='GenerateResource', AssemblyFile=native(sdk / 'Microsoft.Build.Tasks.Core.dll'))
target = E.SubElement(p, 'Target', Name='Generate', DependsOnTargets='GenerateResourcesSource;GenerateAssemblyInfo')
task = E.SubElement(target, 'GenerateResource', Sources='$(StringResourcesPath)',
                    OutputResources=native(out / 'generated/Strings.resources'), ExecuteAsTool='false')
E.SubElement(target, 'CheckReleaseVersion')
E.SubElement(target, 'WriteLinesToFile', File=native(out / 'compile-items.txt'), Lines="@(Compile->'%(FullPath)')", Overwrite='true')
E.SubElement(target, 'WriteLinesToFile', File=native(out / 'references.txt'), Lines='@(Reference)', Overwrite='true')
E.SubElement(target, 'WriteLinesToFile', File=native(out / 'properties.txt'),
             Lines='$(AssemblyVersion);$(AssemblyFileVersion);$(AllowUnsafeBlocks);$(GenerateTargetFrameworkAttribute)', Overwrite='true')
E.ElementTree(p).write(out / 'Generate.csproj', encoding='utf-8', xml_declaration=True)
run('generate', [host8, 'msbuild', out / 'Generate.csproj', '-t:Generate', '-nologo', '-v:minimal'])
properties = (out / 'properties.txt').read_text(encoding='utf-8-sig').splitlines()
assert properties == ['4.0.2.0', '4.6.25519.03', 'true', 'false'], properties
files = [Path(s) for s in (out / 'compile-items.txt').read_text(encoding='utf-8-sig').splitlines()]
original_files = [f for f in files if f.is_relative_to(source)]
assert len(original_files) == 11, [str(f) for f in original_files]
assert all(f.is_file() for f in files)
original_protected = component / 'src/System/Security/Cryptography/ProtectedData.cs'
text = original_protected.read_text()
old_field = '    public static partial class ProtectedData\n    {\n'
old_fixed = '                fixed (byte* pInputData = inputData, pOptionalEntropy = optionalEntropy)'
assert text.count(old_field) == 1 and text.count(old_fixed) == 1
patched = text.replace(old_field, old_field + '        private static readonly byte[] s_nonEmpty = new byte[1];\n\n')
patched = patched.replace(old_fixed,
    '                // DPAPI rejects a null data pointer, even when the length is zero.\n'
    '                byte[] relevantData = inputData.Length == 0 ? s_nonEmpty : inputData;\n\n'
    '                fixed (byte* pInputData = relevantData, pOptionalEntropy = optionalEntropy)')
import difflib
diff = ''.join(difflib.unified_diff(text.splitlines(True), patched.splitlines(True),
    fromfile='a/src/System.Security.Cryptography.ProtectedData/src/System/Security/Cryptography/ProtectedData.cs',
    tofile='b/src/System.Security.Cryptography.ProtectedData/src/System/Security/Cryptography/ProtectedData.cs'))
assert diff == (here / '0001-handle-empty-input-in-native-DPAPI.patch').read_text()
overlay = out / 'overlay/ProtectedData.cs'
overlay.parent.mkdir()
overlay.write_text(patched)
files = [overlay if f == original_protected else f for f in files]
assert set((out / 'references.txt').read_text(encoding='utf-8-sig').splitlines()) == {
    'System.Diagnostics.Tools', 'System.Resources.ResourceManager', 'System.Runtime',
    'System.Runtime.InteropServices', 'System.Security.Cryptography.Primitives'}
binary = out / 'bin'
binary.mkdir()
key = out / 'public.snk'
key.write_bytes(bytes.fromhex((here / 'Microsoft.pubkey.hex').read_text()))
assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
args = ['/nostdlib+', '/target:library', '/langversion:7.3', '/nullable:disable', '/unsafe+', '/optimize+',
        '/deterministic+', '/debug:portable', '/warn:4', '/warnaserror+', '/define:TRACE', '/publicsign+',
        '/keyfile:"' + native(key) + '"', '/out:"' + native(binary / (name + '.dll')) + '"',
        '/resource:"' + native(out / 'generated/Strings.resources') + '",FxResources.' + name + '.SR.resources']
args += ['/reference:"' + native(r) + '"' for r in refs]
args += ['"' + native(f) + '"' for f in files]
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
run('compile', [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')], host10)
record = dict(source_commit=manifest['source_commit'], source_root=native(source), original_configuration='netstandard-Windows_NT',
              framework_reference_profile='netstandard2.0', original_production_source_changes=1,
              original_source_sha256={f.relative_to(source).as_posix(): sha(f) for f in original_files},
              original_project_sha256=sha(original), original_policy_sha256=sha(component / 'dir.props'),
              production_overlay=dict(path=native(overlay), sha256=sha(overlay), original_sha256=sha(original_protected),
                                      patch_sha256=sha(here / '0001-handle-empty-input-in-native-DPAPI.patch'),
                                      reason='Backport later upstream correction: non-null DPAPI pointer for empty input, cbData remains zero'),
              reference_sha256={native(f): sha(f) for f in refs}, generated_source_sha256={native(f): sha(f) for f in files if f not in original_files},
              output_sha256={ext: sha(binary / (name + '.' + ext)) for ext in ['dll', 'pdb']},
              pinned_source_helper=helper_manifest, original_01721_binary_tool_version_reproduced=False,
              original_version_algorithm_executed=True, release_build_id='20170719.03',
              release_date_algorithm_checked_with_UTC_DateTime_to_avoid_host_timezone_shift=True,
              assembly_version='4.0.2.0', file_version='4.6.25519.03', target_framework_attribute_generated=False,
              commands=commands, formal_package_built=False, other_original_framework_profiles_built=False,
              full_dependency_goal_complete=False)
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
print('PASS ProtectedData4.4.0 Windows NETStandard2 source compile, original resource/version policy, 11 original inputs and one audited empty-input backport')
