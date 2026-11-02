"""Compile three original extension reference profiles and restore legacy attrs."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
import zipfile

archive, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent; sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
key = here / 'inputs/Microsoft.snk'; assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex() == 'b03f5f7f11d50a3a'
profiles = [('System.Reflection.Extensions', 'netstandard1.0'), ('System.Text.Encoding.Extensions', 'netstandard1.0'), ('System.Text.Encoding.Extensions', 'netstandard1.3')]
records, commands = {}, []
def run(label, command):
    result = subprocess.run([str(p) for p in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=[str(p) for p in command], exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-5000:])
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == '5aeee2738338530a92d7f6caa2c7d5f569fed3c4'
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    (out / 'SBRP-LICENSE.txt').write_bytes(tar.extractfile(entries['LICENSE.txt']).read())
    for name, framework in profiles:
        original = 'src/referencePackages/src/' + name.lower() + '/4.3.0/ref/' + framework + '/' + name + '.cs'
        source = out / 'source' / original; source.parent.mkdir(parents=True, exist_ok=True); source.write_bytes(tar.extractfile(entries[original]).read())
        expected = json.loads((here / 'inputs' / (name + '-' + framework + '.json')).read_text())[name + '.dll']
        closure = set()
        def select(ident):
            if ident in closure: return
            assert ident in matrix, ident
            closure.add(ident)
            for ref in matrix[ident]['references']:
                n, version = ref.split(', Version='); select(n + '/' + version.split(',')[0])
        for ref in expected['references']:
            n, version = ref.split(', Version='); select(n + '/' + version.split(',')[0])
        refs = [prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / ident / (ident.split('/')[0] + '.dll') for ident in sorted(closure)]
        assert all(p.is_file() for p in refs)
        folder = out / 'raw' / name / framework; folder.mkdir(parents=True)
        args = ['/nostdlib+', '/target:library', '/refonly', '/unsafe+', '/nullable:disable', '/langversion:latest', '/optimize+',
            '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+', '/keyfile:"' + key.as_posix() + '"',
            '/out:"' + (folder / (name + '.dll')).as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
        args += ['/reference:"' + p.as_posix() + '"' for p in refs] + ['"' + source.as_posix() + '"']
        rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
        run(name + '-' + framework, [prefix / 'lib/dotnet/dotnet.exe', compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
        records[name + '/' + framework] = dict(original_source=original, source_sha256=sha(source),
            source_reference_hashes={p.as_posix(): sha(p) for p in refs}, reference_only=True)
        print('PASS original source reference compilation:', name, framework, flush=True)
tool = out / 'metadata-port'; tool.mkdir(); shutil.copy2(here / 'inputs/RestoreAttributes.cs', tool / 'RestoreAttributes.cs')
package = prefix / 'lib/dotnet/library-packs/mono.cecil.0.11.0.nupkg'
assert sha(package) == 'c32254ab0d8d040d0aed45d8b3e521c319fa035041aa029685341b46b167bb30'
with zipfile.ZipFile(package) as z: (tool / 'Mono.Cecil.dll').write_bytes(z.read('lib/netstandard2.0/Mono.Cecil.dll'))
tree = E.Element('Project', Sdk='Microsoft.NET.Sdk'); props = E.SubElement(tree, 'PropertyGroup')
for n, v in dict(TargetFramework='net8.0', OutputType='Exe', AssemblyName='Port', UseAppHost='false', EnableDefaultItems='false',
    EnableNETAnalyzers='false', NuGetAudit='false', Nullable='enable', TreatWarningsAsErrors='true',
    CscToolPath=(prefix / 'lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap').as_posix(), CscToolExe='csc50.cmd').items(): E.SubElement(props, n).text = v
items = E.SubElement(tree, 'ItemGroup'); E.SubElement(items, 'Compile', Include=(tool / 'RestoreAttributes.cs').as_posix())
E.SubElement(items, 'Reference', Include='Mono.Cecil', HintPath=(tool / 'Mono.Cecil.dll').as_posix())
E.indent(tree); E.ElementTree(tree).write(tool / 'Port.csproj', encoding='utf-8', xml_declaration=True)
(tool / 'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
run('metadata-port-build', [prefix / 'lib/dotnet/dotnet.exe', 'build', tool / 'Port.csproj', '-c', 'Release', '--configfile', tool / 'NuGet.config', '-p:UseSharedCompilation=false', '-v:minimal'])
run('metadata-port', [prefix / 'lib/dotnet/dotnet.exe', tool / 'bin/Release/net8.0/Port.dll', here / 'inputs', out / 'raw', out / 'ref'])
(out / 'results.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive), profiles=records, commands=commands,
    original_source_changes=0, source_metadata_port_restores_original_Text_NS10_signing_attributes=True,
    original_binaries_executed_or_compiler_references=False, runtime_implementations_supplied=False), indent=2) + '\n')
