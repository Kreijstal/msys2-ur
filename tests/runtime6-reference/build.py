"""Compile the original NET6 core reference graph using only its own contract closure."""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, tarfile, xml.etree.ElementTree as E

plan, arcade_archive, out = (Path(p).resolve() for p in sys.argv[1:4])
out.mkdir(exist_ok=True)
here = Path(__file__).resolve().parent
native = lambda p: Path(p).resolve().as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(arcade_archive) == '43a351571629a4f2b54cbe07308fa109b20b7c7511991bba0aefadcf5cb39f7d'
source = Path(json.loads((plan / 'source-inputs.json').read_text())['source_root'])
projects = json.loads((plan / 'projects.json').read_text())
model = json.loads((plan / 'evaluated.json').read_text())
assert set(projects) == set(model) and len(projects) == 137
prefix = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host8 = prefix / 'lib/dotnet/dotnet.exe'
host10 = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
sdk = host8.parent / 'sdk/8.0.131'
ref = out / 'ref/net6.0'
ref.mkdir(parents=True, exist_ok=True)
tools = out / 'tools'
tools.mkdir(exist_ok=True)
env = dict(os.environ, DOTNET_ROOT=native(host8.parent), DOTNET_ROOT_X64=native(host8.parent),
    DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false',
    DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'empty-cache'))

def run(label, cmd, host=host8):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=env | dict(DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent)), timeout=240)
    assert r.returncode == 0, (label, r.returncode)
    return [str(p) for p in cmd]

with tarfile.open(arcade_archive) as t:
    for m in t:
        if m.isfile() and m.name.endswith('/CalculateAssemblyAndFileVersions.cs'):
            (tools / 'CalculateAssemblyAndFileVersions.cs').write_bytes(t.extractfile(m).read())
task = tools / 'bin/Release/net8.0/Runtime6.OriginalVersionTasks.dll'
if not task.is_file():
    p = E.Element('Project', Sdk='Microsoft.NET.Sdk')
    pg = E.SubElement(p, 'PropertyGroup')
    for k, v in dict(TargetFramework='net8.0', AssemblyName='Runtime6.OriginalVersionTasks', EnableDefaultItems='false', EnableNETAnalyzers='false', NuGetAudit='false').items():
        E.SubElement(pg, k).text = v
    ig = E.SubElement(p, 'ItemGroup')
    E.SubElement(ig, 'Compile', Include=native(tools / 'CalculateAssemblyAndFileVersions.cs'))
    for n in ['Microsoft.Build.Framework', 'Microsoft.Build.Utilities.Core', 'NuGet.Versioning']:
        E.SubElement(E.SubElement(ig, 'Reference', Include=n), 'HintPath').text = native(sdk / (n + '.dll'))
    E.ElementTree(p).write(tools / 'Tasks.csproj', encoding='utf-8', xml_declaration=True)
    (tools / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>')
    run('tools', [host8, 'build', tools / 'Tasks.csproj', '-c', 'Release', '--configfile', tools / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])

dependencies = {}
for name, m in model.items():
    assert m['properties']['TargetFramework'] == 'net6.0'
    deps = []
    for i in m['items']['ProjectReference']:
        if i['metadata'].get('ReferenceOutputAssembly', '').lower() == 'false':
            continue
        dep = Path(i['full_path'].replace('\\', '/')).stem
        assert dep in model, (name, dep, i)
        if dep != name and dep not in deps:
            deps.append(dep)
    dependencies[name] = deps
order, seen = [], set()
def visit(name, stack=()):
    if name in seen:
        return
    assert name not in stack, ('Original dependency cycle', stack, name)
    for dep in dependencies[name]:
        visit(dep, stack + (name,))
    seen.add(name)
    order.append(name)
for name in sorted(model):
    visit(name)
(out / 'build-order.json').write_text(json.dumps(dict(order=order, dependencies=dependencies), indent=2) + '\n')

versions = {}
def file_version(major, minor):
    key = major + '.' + minor
    if key in versions:
        return versions[key]
    p = E.Element('Project')
    E.SubElement(p, 'UsingTask', TaskName='Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions', AssemblyFile=native(task))
    target = E.SubElement(p, 'Target', Name='Calculate')
    call = E.SubElement(target, 'Microsoft.DotNet.Arcade.Sdk.CalculateAssemblyAndFileVersions', VersionPrefix=key + '.19', BuildNumber='20230618.6')
    E.SubElement(call, 'Output', TaskParameter='FileVersion', PropertyName='FV')
    E.SubElement(target, 'WriteLinesToFile', File=native(out / ('version-' + key + '.txt')), Lines='$(FV)', Overwrite='true')
    E.ElementTree(p).write(out / ('Version-' + key + '.proj'), encoding='utf-8', xml_declaration=True)
    run('version-' + key, [host8, 'msbuild', out / ('Version-' + key + '.proj'), '-t:Calculate', '-nologo', '-v:minimal'])
    result = (out / ('version-' + key + '.txt')).read_text(encoding='utf-8-sig').strip()
    assert result == ('11.100.1923.31806' if key == '11.1' else '6.0.1923.31806'), (key, result)
    versions[key] = result
    return result

records = {}
for name in order:
    m = model[name]
    props = m['properties']
    folder = out / 'projects' / name
    folder.mkdir(parents=True, exist_ok=True)
    files = list(dict.fromkeys(Path(i['full_path']).resolve() for i in m['items']['Compile']))
    assert files and all(p.is_file() and p.is_relative_to(source) for p in files), (name, files)
    key = folder / 'public.snk'
    key.write_bytes(bytes.fromhex((here / 'keys' / (props['StrongNameKeyId'] + '.pubkey.hex')).read_text()))
    av = props['AssemblyVersion']
    assert av
    fv = file_version(props['MajorVersion'], props['MinorVersion'])
    attrs = ['[assembly:System.Reflection.AssemblyVersion(' + json.dumps(av) + ')]',
        '[assembly:System.Reflection.AssemblyFileVersion(' + json.dumps(fv) + ')]',
        '[assembly:System.Reflection.AssemblyInformationalVersion("6.0.19+source-runtime.e37fab9fc9f7bce120a7165491ed392a73f8ab51")]',
        '[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v6.0")]']
    if props['CLSCompliant'].lower() == 'true':
        attrs.append('[assembly:System.CLSCompliant(true)]')
    for i in m['items']['AssemblyInfoLines']:
        if 'ReferenceAssembly' not in i['identity']:
            attrs.append(i['identity'])
    for i in m['items']['AssemblyMetadata']:
        attrs.append('[assembly:System.Reflection.AssemblyMetadata(' + json.dumps(i['identity']) + ',' + json.dumps(i['metadata'].get('Value', '')) + ')]')
    info = folder / 'AssemblyInfo.cs'
    info.write_text('\n'.join(attrs) + '\n')
    closure = set()
    def add(n):
        for dep in dependencies[n]:
            if dep not in closure:
                closure.add(dep)
                add(dep)
    add(name)
    references = [ref / (n + '.dll') for n in order if n in closure]
    assert all(p.is_file() for p in references)
    defines = list(dict.fromkeys(props['DefineConstants'].replace(',', ';').split(';') +
        ['TRACE', 'NET', 'NETCOREAPP', 'NET6_0', 'NET5_0_OR_GREATER', 'NET6_0_OR_GREATER',
         *['NETCOREAPP' + s + '_OR_GREATER' for s in ['1_0', '1_1', '2_0', '2_1', '2_2', '3_0', '3_1']]]))
    args = ['/nostdlib+', '/target:library', '/refonly', '/deterministic+', '/runtimemetadataversion:v4.0.30319',
        '/nullable:' + (props['Nullable'] or 'disable'), '/langversion:' + props['LangVersion'],
        '/unsafe' + ('+' if props['AllowUnsafeBlocks'].lower() == 'true' else '-'),
        '/checked' + ('+' if props['CheckForOverflowUnderflow'].lower() == 'true' else '-'),
        '/publicsign+', '/keyfile:"' + native(key) + '"', '/out:"' + native(ref / (name + '.dll')) + '"',
        '/define:' + ';'.join(x for x in defines if x), '/features:' + props['Features'].replace(';', ',')]
    if props['NoWarn']:
        args.append('/nowarn:' + props['NoWarn'].replace(';', ','))
    if props['TreatWarningsAsErrors'].lower() == 'true':
        args.append('/warnaserror+')
    args += ['/reference:"' + native(p) + '"' for p in references]
    args += ['"' + native(p) + '"' for p in files + [info]]
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    fingerprint = dict(original_sources={p.relative_to(source).as_posix(): sha(p) for p in files},
        assembly_info_sha256=sha(info), response_sha256=sha(rsp), dependency_sha256={p.name: sha(p) for p in references},
        compiler_sha256=sha(compiler), public_key_sha256=sha(key))
    stamp = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    result_path = folder / 'results.json'
    if result_path.is_file() and (ref / (name + '.dll')).is_file():
        previous = json.loads(result_path.read_text())
        if previous.get('fingerprint') == stamp and previous.get('output_sha256') == sha(ref / (name + '.dll')):
            records[name] = previous
            print('Cached', name, flush=True)
            continue
    cmd = [host10, compiler, '-noconfig', '@' + native(rsp)]
    with (folder / 'compile.log').open('w', encoding='utf-8') as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
            env=env | dict(DOTNET_ROOT=native(host10.parent), DOTNET_ROOT_X64=native(host10.parent)), timeout=240)
    record = fingerprint | dict(command=[str(p) for p in cmd], exit_code=r.returncode,
        framework='net6.0', assembly_version=av, file_version=fv, strong_name_key=props['StrongNameKeyId'],
        original_production_source_changes=0, fingerprint=stamp)
    assert r.returncode == 0, (name, r.returncode, str(folder / 'compile.log'))
    record['output_sha256'] = sha(ref / (name + '.dll'))
    result_path.write_text(json.dumps(record, indent=2) + '\n')
    records[name] = record
    (out / 'progress.json').write_text(json.dumps(records, indent=2) + '\n')
    print('PASS', name, av, fv, len(files), 'original Compile inputs', flush=True)
(out / 'results.json').write_text(json.dumps(dict(projects=records, source_root=native(source),
    source_commit='e37fab9fc9f7bce120a7165491ed392a73f8ab51', original_arcade_commit='3d9c9a4d3d893e903bb3295fd5b55b8e40699888',
    original_version_task_executed=True, original_build_number='20230618.6', original_core_contract_projects=137,
    compatibility_facades_built=False, complete_targeting_pack_built=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS 137 original NET6 core references; metadata/source/consumer validation remains required')
