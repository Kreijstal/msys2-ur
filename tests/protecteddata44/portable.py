"""Build the original non-Windows NETStandard profile using a disclosed PNSE source helper."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, xml.etree.ElementTree as E

build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((build / 'results.json').read_text())
source = Path(record['source_root'])
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs = sorted((prefix / 'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs) == 113
name = 'System.Security.Cryptography.ProtectedData'
component = source / 'src' / name
original_ref = component / 'ref' / (name + '.cs')
generated = out / 'generated'
generated.mkdir()
helper = here / 'buildtools-resource-helper'
genfacades = prefix / 'lib/dotnet/tool-packs/genfacades-10.0.5-bootstrap/tools/net/Microsoft.DotNet.GenFacades.dll'
roslyn = prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap'
p = E.Element('Project')
pg = E.SubElement(p, 'PropertyGroup')
values = dict(TargetGroup='netstandard', OSGroup='Unix', TargetsWindows='false', ConfigurationGroup='Release',
    TargetFramework='netstandard2.0', AssemblyName=name, CommonPath=native(source / 'src/Common/src'),
    GenerateTargetFrameworkAttribute='false', AssemblyVersion='4.0.2.0', MajorVersion='4', MinorVersion='6',
    BuildNumberMajor='25519', BuildNumberMinor='03', LatestCommit=record['source_commit'] + '+msys2-pnse-source-helper',
    BuildToolsTaskDir=native(build / 'tools/bin/Release/net8.0') + '/',
    IntermediateOutputPath=native(generated) + '/', StringResourcesPath=native(component / 'src/Resources/Strings.resx'),
    CLSCompliant='true', IsDotNetFrameworkProductAssembly='true')
for k, v in values.items():
    E.SubElement(pg, k).text = v
E.SubElement(p, 'Import', Project=native(build / 'upstream.proj'))
ig = E.SubElement(p, 'ItemGroup')
E.SubElement(E.SubElement(ig, 'AssemblyMetadata', Include='NotSupported'), 'Value').text = 'True'
item = E.SubElement(ig, 'PnseInput', Include=native(original_ref))
E.SubElement(item, 'OutputPath').text = native(generated / 'NotSupported.cs')
E.SubElement(p, 'Import', Project=native(helper / 'resources.targets'))
E.SubElement(p, 'Import', Project=native(helper / 'versioning.targets'))
E.SubElement(p, 'UsingTask', TaskName='NotSupportedAssemblyGenerator', AssemblyFile=native(genfacades))
E.SubElement(p, 'UsingTask', TaskName='GenerateResource', AssemblyFile=native(host8.parent / 'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'))
target = E.SubElement(p, 'Target', Name='Generate', DependsOnTargets='GenerateResourcesSource;GenerateAssemblyInfo')
E.SubElement(target, 'Error', Condition="'$(GeneratePlatformNotSupportedAssemblyMessage)' != 'SR.PlatformNotSupported_CryptographyProtectedData'", Text='Original portable profile/message mismatch')
E.SubElement(target, 'NotSupportedAssemblyGenerator', SourceFiles='@(PnseInput)', LangVersion='7.3',
    Message='$(GeneratePlatformNotSupportedAssemblyMessage)', RoslynAssembliesPath=native(roslyn))
E.SubElement(target, 'GenerateResource', Sources='$(StringResourcesPath)', OutputResources=native(generated / 'Strings.resources'), ExecuteAsTool='false')
E.SubElement(target, 'WriteLinesToFile', File=native(out / 'compile-items.txt'), Lines="@(Compile->'%(FullPath)')", Overwrite='true')
E.ElementTree(p).write(out / 'Generate.csproj', encoding='utf-8', xml_declaration=True)
commands = []

def run(label, host, cmd):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=180)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode)

run('generate', host8, [host8, 'msbuild', out / 'Generate.csproj', '-t:Generate', '-nologo', '-v:minimal'])
files = [Path(s) for s in (out / 'compile-items.txt').read_text(encoding='utf-8-sig').splitlines()]
original_files = [f for f in files if f.is_relative_to(source)]
assert original_files == [source / 'src/Common/src/System/SR.cs'], original_files
files.append(generated / 'NotSupported.cs')
assert 'NotSupported' in (generated / '_AssemblyInfo.cs').read_text(encoding='utf-8-sig')
binary = out / 'bin'
binary.mkdir()
args = ['/nostdlib+', '/target:library', '/langversion:7.3', '/nullable:disable', '/optimize+', '/deterministic+',
    '/debug:portable', '/warn:4', '/warnaserror+', '/define:TRACE', '/publicsign+',
    '/keyfile:"' + native(build / 'public.snk') + '"', '/out:"' + native(binary / (name + '.dll')) + '"',
    '/resource:"' + native(generated / 'Strings.resources') + '",FxResources.' + name + '.SR.resources']
args += ['/reference:"' + native(p) + '"' for p in refs] + ['"' + native(f) + '"' for f in files]
(out / 'compile.rsp').write_text('\n'.join(args) + '\n')
run('compile', host10, [host10, compiler, '-noconfig', '@' + native(out / 'compile.rsp')])
r = dict(source_root=native(source), source_commit=record['source_commit'], original_configuration='netstandard',
    framework_reference_profile='netstandard2.0', original_message_expression='SR.PlatformNotSupported_CryptographyProtectedData',
    original_contract_source_sha256=sha(original_ref), original_common_SR_sha256=sha(original_files[0]),
    generated_source_sha256={native(f): sha(f) for f in files if f not in original_files},
    output_sha256={ext: sha(binary / (name + '.' + ext)) for ext in ['dll', 'pdb']},
    portable_generator_helper='Installed source GenFacades10 unsupported-source task, NET8 bootstrap with source Roslyn5 helper',
    portable_generator_helper_sha256=sha(genfacades), original_2017_GenAPI_tool_reproduced=False,
    assembly_version='4.0.2.0', file_version='4.6.25519.03', target_framework_attribute_generated=False,
    original_production_source_changes=0, commands=commands, formal_package_built=False,
    other_original_framework_profiles_built=False, full_dependency_goal_complete=False)
(out / 'results.json').write_text(json.dumps(r, indent=2) + '\n')
print('PASS original portable NETStandard configuration and resources, generated PNSE methods using the disclosed source helper')
