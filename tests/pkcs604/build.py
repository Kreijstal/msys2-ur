"""Compile unchanged Pkcs6.0.4 profiles with original Arcade6 tasks and NET6 contracts."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tarfile, xml.etree.ElementTree as E

plan, arcade_archive, reference_root, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(arcade_archive) == '43a351571629a4f2b54cbe07308fa109b20b7c7511991bba0aefadcf5cb39f7d'
source = Path(json.loads((plan / 'source-inputs.json').read_text())['source_root'])
model = json.loads((plan / 'evaluated.json').read_text())
reference_records = json.loads((reference_root / 'build/results.json').read_text())
reference_audit = json.loads((reference_root / 'source-audit.json').read_text())
reference_checks = json.loads((reference_root / 'check/results.json').read_text())
assert reference_records['original_core_contract_projects'] == reference_audit['original_core_contract_projects'] == 137
assert reference_checks['all_original_metadata_and_reference_closure_checks_passed']
refs = sorted((reference_root / 'build/ref/net6.0').glob('*.dll'))
assert len(refs) == 137
for p in refs:
    assert sha(p) == reference_records['projects'][p.stem]['output_sha256']
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
sdk = host8.parent / 'sdk/8.0.131'
tools = out / 'tools'
tools.mkdir()
with tarfile.open(arcade_archive) as t:
    for m in t:
        if not m.isfile():
            continue
        name = Path(m.name).name
        if name in ['CalculateAssemblyAndFileVersions.cs', 'GenerateResxSource.cs']:
            (tools / name).write_bytes(t.extractfile(m).read())
        if name == 'ProjectDefaults.props' and '/Microsoft.DotNet.Arcade.Sdk/' in m.name:
            assert t.extractfile(m).read() == (here / 'inputs/Arcade6.ProjectDefaults.props').read_bytes()
commands = []
def run(label, folder, host, cmd):
    with (folder / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
            DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent), MSBuildEnableWorkloadResolver='false',
            DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'empty-cache')), timeout=240)
    commands.append(dict(command=[str(p) for p in cmd], exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode, str(folder / (label + '.log')))

p = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(p, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', AssemblyName='Pkcs6.OriginalTasks', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false').items():
    E.SubElement(pg, k).text = v
ig = E.SubElement(p, 'ItemGroup')
for name in ['CalculateAssemblyAndFileVersions.cs', 'GenerateResxSource.cs']:
    E.SubElement(ig, 'Compile', Include=native(tools / name))
for name in ['Microsoft.Build.Framework', 'Microsoft.Build.Utilities.Core', 'NuGet.Versioning']:
    E.SubElement(E.SubElement(ig, 'Reference', Include=name), 'HintPath').text = native(sdk / (name + '.dll'))
E.ElementTree(p).write(tools / 'Tasks.csproj', encoding='utf-8', xml_declaration=True)
(tools / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
run('tasks', tools, host8, [host8, 'build', tools / 'Tasks.csproj', '-c', 'Release', '--configfile', tools / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
task = tools / 'bin/Release/net8.0/Pkcs6.OriginalTasks.dll'
records = {}
for label, entry in model.items():
    folder = out / label
    folder.mkdir()
    binary = folder / 'bin'
    binary.mkdir()
    props = entry['properties']
    assert props['TargetFramework'] == ('net6.0-windows' if label == 'windows' else 'net6.0')
    assert props['ServicingVersion'] == '4' and props['StrongNameKeyId'] == 'Microsoft'
    files = list(dict.fromkeys(Path(i['full_path']).resolve() for i in entry['items']['Compile']))
    assert files and all(p.is_relative_to(source) and p.is_file() for p in files)
    original_hashes = {p.relative_to(source).as_posix(): sha(p) for p in files}
    edges = [Path(i['full_path']).stem for i in entry['items']['ProjectReference'] if i['metadata'].get('ReferenceOutputAssembly', 'true').lower() != 'false']
    assert edges == ['System.Formats.Asn1'], edges
    for i in entry['items']['Reference']:
        assert (reference_root / 'build/ref/net6.0' / (i['identity'] + '.dll')).is_file(), i
    p = E.Element('Project')
    for name in ['CalculateAssemblyAndFileVersions', 'GenerateResxSource']:
        E.SubElement(p, 'UsingTask', TaskName='Microsoft.DotNet.Arcade.Sdk.' + name, AssemblyFile=native(task))
    for name in ['GenerateResource', 'XslTransformation']:
        E.SubElement(p, 'UsingTask', TaskName=name, AssemblyFile=native(sdk / 'Microsoft.Build.Tasks.Core.dll'))
    target = E.SubElement(p, 'Target', Name='Generate')
    call = E.SubElement(target, 'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions', VersionPrefix='6.0.19', BuildNumber='20230618.6')
    E.SubElement(call, 'Output', TaskParameter='FileVersion', PropertyName='FV')
    E.SubElement(target, 'WriteLinesToFile', File=native(folder / 'file-version.txt'), Lines='$(FV)', Overwrite='true')
    generated = []
    resources = []
    for i in entry['items']['EmbeddedResource']:
        resx = Path(i['full_path'])
        logical = i['metadata']['ManifestResourceName']
        generated_file = folder / 'SR.Generated.cs'
        E.SubElement(target, 'Microsoft.DotNet.Arcade.Sdk.GenerateResxSource', Language='C#', ResourceFile=native(resx),
            ResourceName=logical, ResourceClassName=i['metadata']['ClassName'], OmitGetResourceString='true', OutputPath=native(generated_file))
        resource = folder / 'Strings.resources'
        E.SubElement(target, 'GenerateResource', Sources=native(resx), OutputResources=native(resource), ExecuteAsTool='false')
        generated.append(generated_file)
        resources.append((resx, resource, logical + '.resources'))
    asn = []
    xslt = source / 'src/libraries/Common/src/System/Security/Cryptography/Asn1/asn.xslt'
    for i, item in enumerate(entry['items']['AsnXml']):
        xml = Path(item['identity']).resolve()
        assert xml.is_file() and Path(str(xml) + '.cs').is_file()
        dest = folder / (str(i) + '-' + xml.name + '.cs')
        E.SubElement(target, 'XslTransformation', XslInputPath=native(xslt), XmlInputPaths=native(xml), OutputPaths=native(dest))
        asn.append((xml, dest))
    E.ElementTree(p).write(folder / 'Generate.proj', encoding='utf-8', xml_declaration=True)
    run('generate', folder, host8, [host8, 'msbuild', folder / 'Generate.proj', '-t:Generate', '-nologo', '-v:minimal'])
    assert (folder / 'file-version.txt').read_text(encoding='utf-8-sig').strip() == '6.0.1923.31806'
    for xml, dest in asn:
        assert dest.read_bytes().replace(b'\r\n', b'\n') == Path(str(xml) + '.cs').read_bytes().replace(b'\r\n', b'\n'), xml
    key = folder / 'public.snk'
    key.write_bytes(bytes.fromhex((here / 'Microsoft.pubkey.hex').read_text()))
    assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
    attrs = ['[assembly:System.Reflection.AssemblyVersion("6.0.0.0")]',
        '[assembly:System.Reflection.AssemblyFileVersion("6.0.1923.31806")]',
        '[assembly:System.Reflection.AssemblyInformationalVersion("6.0.19+source-runtime.e37fab9fc9f7bce120a7165491ed392a73f8ab51")]',
        '[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v6.0")]',
        '[assembly:System.CLSCompliant(true)]', '[assembly:System.Resources.NeutralResourcesLanguage("en-US")]',
        '[assembly:System.Runtime.InteropServices.DefaultDllImportSearchPaths(System.Runtime.InteropServices.DllImportSearchPath.AssemblyDirectory | System.Runtime.InteropServices.DllImportSearchPath.System32)]',
        '[assembly:System.Runtime.Versioning.' + ('SupportedOSPlatform("windows")' if label == 'windows' else 'UnsupportedOSPlatform("browser")') + ']']
    for i in entry['items']['AssemblyMetadata']:
        attrs.append('[assembly:System.Reflection.AssemblyMetadata(' + json.dumps(i['identity']) + ',' + json.dumps(i['metadata'].get('Value', '')) + ')]')
    info = folder / 'AssemblyInfo.cs'
    info.write_text('\n'.join(attrs) + '\n')
    defines = ['TRACE', 'NET', 'NETCOREAPP', 'NET6_0', 'NET5_0_OR_GREATER', 'NET6_0_OR_GREATER']
    defines += ['NETCOREAPP' + x + '_OR_GREATER' for x in ['1_0', '1_1', '2_0', '2_1', '2_2', '3_0', '3_1']]
    if label == 'windows':
        defines += ['WINDOWS', 'WINDOWS7_0', 'WINDOWS7_0_OR_GREATER']
    defines += [s for s in props['DefineConstants'].replace(',', ';').split(';') if s]
    dest = binary / 'System.Security.Cryptography.Pkcs.dll'
    args = ['/nostdlib+', '/target:library', '/deterministic+', '/debug:portable', '/optimize+', '/unsafe+', '/nullable:' + props['Nullable'],
        '/langversion:' + props['LangVersion'], '/features:' + props['Features'].replace(';', ','), '/publicsign+',
        '/keyfile:"' + native(key) + '"', '/out:"' + native(dest) + '"', '/define:' + ';'.join(dict.fromkeys(defines))]
    if props['TreatWarningsAsErrors'].lower() == 'true':
        args.append('/warnaserror+')
    if props['NoWarn']:
        args.append('/nowarn:' + props['NoWarn'].replace(';', ','))
    if props['GenerateDocumentationFile'].lower() == 'true':
        args.append('/doc:"' + native(dest.with_suffix('.xml')) + '"')
    args += ['/reference:"' + native(p) + '"' for p in refs]
    args += ['/resource:"' + native(p) + '",' + name for _, p, name in resources]
    args += ['"' + native(p) + '"' for p in files + generated + [info]]
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    run('compile', folder, host10, [host10, compiler, '-noconfig', '@' + native(rsp)])
    record = dict(framework=props['TargetFramework'], assembly_version='6.0.0.0', file_version='6.0.1923.31806', NuGet_version='6.0.4',
        original_source_sha256=original_hashes, original_resource_sha256={p.relative_to(source).as_posix(): sha(p) for p, _, _ in resources},
        original_project_reference_edges=edges, source_NET6_reference_sha256={p.name: sha(p) for p in refs},
        generated_source_sha256={native(p): sha(p) for p in generated + [info]},
        original_AsnXml_regeneration={p.relative_to(source).as_posix(): dict(xml_sha256=sha(p), checked_in_cs_sha256=sha(Path(str(p) + '.cs')), generated_sha256=sha(g)) for p, g in asn},
        original_AsnXml_outputs_match_ignoring_only_line_endings=True, original_xslt_sha256=sha(xslt),
        output_sha256={p.suffix.lstrip('.'): sha(p) for p in binary.iterdir() if p.is_file()}, original_production_source_changes=0)
    records[label] = record
    (out / 'progress.json').write_text(json.dumps(records, indent=2) + '\n')
    print('PASS', label, props['TargetFramework'], len(files), 'original Compile inputs;', len(asn), 'original ASN.1 regenerations', flush=True)
(out / 'results.json').write_text(json.dumps(dict(source_root=native(source), source_commit='e37fab9fc9f7bce120a7165491ed392a73f8ab51',
    projects=records, commands=commands, original_arcade_version_and_resource_tasks_executed=True,
    private_original_NET6_core_reference_root=native(reference_root), complete_NET6_targeting_pack_built=False,
    other_original_Pkcs_framework_profiles_built=False, formal_package_built=False, full_dependency_goal_complete=False), indent=2) + '\n')
