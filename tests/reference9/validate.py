"""Audit all original contracts and compile a consumer requiring .NET9 APIs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E

root, out = (Path(p).resolve() for p in sys.argv[1:3])
installed_refs=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else None
if installed_refs is not None:
    assert {p.name for p in installed_refs.glob('*.dll')}=={p.name for p in (out/'ref/net9.0').glob('*.dll')}
    for p in installed_refs.glob('*.dll'):assert p.read_bytes()==(out/'ref/net9.0'/p.name).read_bytes(),p
here = Path(__file__).resolve().parent
native_root = subprocess.check_output(['cygpath', '-am', str(root)], text=True).strip()
def native(path):
    path = Path(path).resolve()
    if path.is_relative_to(root):
        return native_root + '/' + path.relative_to(root).as_posix()
    return subprocess.check_output(['cygpath', '-am', str(path)], text=True).strip()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
status = json.loads((out / 'build-status.json').read_text())
assert status['complete_declared_reference_graph']
assert set(status['projects']) == set(json.loads((out / 'projects.json').read_text()))
original_cs = {}
for name, entry in status['projects'].items():
    assert entry['exit_code'] == 0
    for path, expected in entry['source_cs'].items():
        file = root / 'r' / path if not (len(path) > 1 and path[1] == ':') else root / path.replace('\\', '/')[len(native_root) + 1:]
        assert sha(file) == expected, (name, path)
        if file.is_relative_to(root / 'r'):
            original_cs[path] = expected
    output = out / ('stubs' if entry['kind'] == 'stub' else 'ref/net9.0') / (name.removeprefix('stub:') + '.dll')
    assert sha(output) == entry['output_sha256'], name
for path, expected in json.loads((out / 'source-projects.json').read_text()).items():
    assert sha(root / 'r' / path) == expected, path
tool = out / 'audit-tool'
tool.mkdir()
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk')
pg = E.SubElement(tree, 'PropertyGroup')
for k, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='AuditReferencePack9',
                 UseAppHost='false', EnableDefaultItems='false', EnableNETAnalyzers='false',
                 NuGetAudit='false', Nullable='enable').items():
    E.SubElement(pg, k).text = v
ig = E.SubElement(tree, 'ItemGroup')
E.SubElement(ig, 'Compile', Include=native(here / 'inputs/AuditReferencePack.cs'))
E.ElementTree(tree).write(tool / 'Build.csproj', encoding='utf-8', xml_declaration=True)
dotnet = '/clang64/lib/dotnet/dotnet.exe'
def run(command, log, success=True):
    with log.open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    if success:
        assert result.returncode == 0, (command, result.returncode, log)
    return result.returncode
run([dotnet, 'build', native(tool / 'Build.csproj'), '-c', 'Release', '--configfile', native(out / 'NuGet.config'),
     '-p:UseSharedCompilation=false', '-v:minimal'], out / 'audit-build.log')
run([dotnet, native(tool / 'bin/Release/net8.0/AuditReferencePack9.dll'), native(out)], out / 'metadata-audit.json')
audit = json.loads((out / 'metadata-audit.json').read_text())
consumer = out / 'consumer'
consumer.mkdir()
cases = {}
compiler = Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')
for name, refs in [('net9', sorted((installed_refs or out/'ref/net9.0').glob('*.dll'))),
                   ('net8-negative-control', sorted(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0').glob('*.dll')))]:
    assert refs
    args = ['/nostdlib+', '/target:exe', '/optimize+', '/deterministic+', '/langversion:preview',
            '/out:"' + native(consumer / (name + '.dll')) + '"',
            *['/reference:"' + native(p) + '"' for p in refs],
            '"' + native(here / 'inputs/Net9Consumer.cs') + '"']
    rsp = consumer / (name + '.rsp')
    rsp.write_text('\n'.join(args) + '\n')
    command = [dotnet, native(compiler), '-noconfig', '@' + native(rsp)]
    code = run(command, consumer / (name + '.log'), success=name == 'net9')
    if name != 'net9':
        log = (consumer / (name + '.log')).read_text()
        assert code != 0 and 'CountBy' in log and 'Lock' in log, log
    cases[name] = dict(command=command, exit_code=code, references=len(refs),
                       reference_files_sha256={p.name: sha(p) for p in refs})
result = dict(original_cs_inputs=len(original_cs), all_original_source_and_output_hashes_match=True,
              metadata_audit=audit, consumer_cases=cases, consumer_executed=False,
              formal_pacman_installed=installed_refs is not None, private_reference_graph_complete=True, reference_pack_generators_complete=False,
              full_framework9_built=False, full_sdk10_built=False, full_dependency_goal_complete=False)
(out / 'validation-results.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS complete original public contract/stub metadata graph; net9 API consumer compiles and net8 control rejects it')
