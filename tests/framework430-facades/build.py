"""Build all original profiles of seven original legacy NuGet packages."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import subprocess
import sys
import tarfile
import zipfile

sbrp, corefx, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(sbrp) == '2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
assert sha(corefx) == '1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
profiles = json.loads((here / 'inputs/baselines1/profiles.json').read_text())
resources = json.loads((here / 'inputs/reference-data.json').read_text())
commands = []; records = {}; original_hashes = {}
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
def extract(tar, entries, name, kind):
    data = tar.extractfile(entries[name]).read(); path = out / 'source' / kind / name
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); original_hashes[kind + '/' + name] = hashlib.sha256(data).hexdigest(); return path
with tarfile.open(sbrp) as st, tarfile.open(corefx) as ct:
    assert st.pax_headers['comment'] == '5aeee2738338530a92d7f6caa2c7d5f569fed3c4'
    assert ct.pax_headers['comment'] == '4d1af962ca0fede10beb01d197367c2f90e92c97'
    se = {m.name.partition('/')[2]: m for m in st if m.isfile()}; ce = {m.name.partition('/')[2]: m for m in ct if m.isfile()}
    for name in ['LICENSE.txt']: extract(st, se, name, 'sbrp')
    for name in ['LICENSE', 'THIRD-PARTY-NOTICES']: extract(ct, ce, name, 'corefx')
    # The original FileSystem reference names the older 4.0.0 compiler contract.
    # Build its complete enum API from unchanged CoreFX source; do not substitute
    # the later 4.0.1 assembly from the 4.3.0 parent NuGet.
    private = out / 'private-contracts/System.IO.FileSystem.Primitives/4.0.0.0'; private.mkdir(parents=True)
    original = extract(ct, ce, 'src/System.IO.FileSystem.Primitives/ref/System.IO.FileSystem.Primitives.cs', 'corefx')
    expected = next(iter(json.loads((here / 'inputs/FSPrimitives400.json').read_text()).values()))
    info = ['[assembly:System.Reflection.AssemblyVersion("4.0.0.0")]']
    for attribute in expected['attributes']:
        full = attribute['type']
        if full in ['System.Runtime.CompilerServices.CompilationRelaxationsAttribute', 'System.Runtime.CompilerServices.RuntimeCompatibilityAttribute', 'System.Diagnostics.DebuggableAttribute']: continue
        values = [str(v).lower() if full == 'System.CLSCompliantAttribute' else json.dumps(v, ensure_ascii=True) for v in attribute['arguments']]
        info.append('[assembly:global::' + full + '(' + ','.join(values) + ')]')
    (private / 'AssemblyInfo.cs').write_text('\n'.join(info) + '\n')
    runtime = prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime/4.0.0.0/System.Runtime.dll'
    private_args = ['/nostdlib+', '/target:library', '/refonly', '/optimize+', '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+', '/keyfile:"' + (here / 'inputs/Microsoft.snk').as_posix() + '"', '/out:"' + (private / 'System.IO.FileSystem.Primitives.dll').as_posix() + '"', '/reference:"' + runtime.as_posix() + '"', '"' + original.as_posix() + '"', '"' + (private / 'AssemblyInfo.cs').as_posix() + '"']
    (private / 'compile.rsp').write_text('\n'.join(private_args) + '\n')
    run('private-FSPrimitives400', [prefix / 'lib/dotnet/dotnet.exe', compiler / 'csc.dll', '-noconfig', '@' + str(private / 'compile.rsp')])
    run('private-inspector-build', [sys.executable, here / 'build-inspector.py', out / 'inspector', prefix])
    run('private-FSPrimitives400-inspect', [prefix / 'lib/dotnet/dotnet.exe', out / 'inspector/bin/Release/net8.0/Inspect.dll', private / 'metadata.json', private / 'System.IO.FileSystem.Primitives.dll'])
    actual = json.loads((private / 'metadata.json').read_text())['System.IO.FileSystem.Primitives.dll']
    canon = lambda rows: sorted(json.dumps(r, sort_keys=True) for r in rows)
    assert actual['identity'] == expected['identity'] and actual['api'] == expected['api'] and actual['references'] == expected['references'] and canon(actual['attributes']) == canon(expected['attributes']), ('private old compiler contract', actual)
    matrix['System.IO.FileSystem.Primitives/4.0.0.0'] = dict(references=expected['references'])
    net = out / 'private-contracts/System.Net.Primitives/4.0.10.0'; net.mkdir(parents=True)
    source_net_policy = json.loads((here / 'inputs/source-NetPrimitives-provenance.json').read_text())
    source_net_package = prefix / 'lib/dotnet/library-packs' / source_net_policy['installed_source_package']
    assert sha(source_net_package) == source_net_policy['source_NuGet_sha256']
    with zipfile.ZipFile(source_net_package) as z: (net / 'System.Net.Primitives.dll').write_bytes(z.read(source_net_policy['asset']))
    net_expected = json.loads((here / 'inputs/source-System.Net.Primitives-4010.json').read_text())['System.Net.Primitives.dll']
    matrix['System.Net.Primitives/4.0.10.0'] = dict(references=net_expected['references'])
    private_refs = {'System.IO.FileSystem.Primitives/4.0.0.0':private / 'System.IO.FileSystem.Primitives.dll', 'System.Net.Primitives/4.0.10.0':net / 'System.Net.Primitives.dll'}
    for label, row in profiles.items():
        name, tfm = row['name'], row['framework']; baseline = json.loads((here / 'inputs' / (label + '.json')).read_text())[name + '.dll']
        raw = extract(st, se, 'src/referencePackages/src/' + name.lower() + '/4.3.0/ref/' + tfm + '/' + name + '.cs', 'sbrp')
        folder = out / 'raw' / name / tfm; folder.mkdir(parents=True); sources = [raw]
        closure = set()
        def select(ident):
            if ident in closure: return
            assert ident in matrix, ident
            closure.add(ident)
            for ref in matrix[ident]['references']:
                n, v = ref.split(', Version='); select(n + '/' + v.split(',')[0])
        for ref in baseline['references']:
            n, v = ref.split(', Version='); select(n + '/' + v.split(',')[0])
        chosen = {}
        for ident in sorted(closure):
            n, version = ident.split('/')
            if n not in chosen or tuple(map(int, version.split('.'))) > tuple(map(int, chosen[n].split('/')[1].split('.'))): chosen[n] = ident
        refs = [private_refs[ident] if ident in private_refs else prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / ident / (ident.split('/')[0] + '.dll') for ident in chosen.values()]
        assert all(p.is_file() for p in refs)
        v = next(r['native_version'] for r in resources if r['name'] == name and '/' + tfm + '/' in r['file']); language = 1033 if v['Language'] == 'English (United States)' else 0
        assert v['Language'] in ['English (United States)', 'Language Neutral']
        rc = ['LANGUAGE 9,1' if language else 'LANGUAGE 0,0', '1 VERSIONINFO', 'FILEVERSION ' + ','.join(re.findall(r'\d+', v['FileVersion'])[:4]), 'PRODUCTVERSION ' + ','.join(re.findall(r'\d+', v['ProductVersion'])[:4]), 'FILEFLAGSMASK 0x3f', 'FILEFLAGS 0', 'FILEOS 4', 'FILETYPE 2', 'FILESUBTYPE 0', 'BEGIN', 'BLOCK "StringFileInfo"', 'BEGIN', 'BLOCK "040904b0"' if language else 'BLOCK "000004b0"', 'BEGIN']
        for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']: rc.append('VALUE ' + json.dumps(field) + ', L' + json.dumps(v[field], ensure_ascii=True).replace('\\u','\\x'))
        rc += ['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", ' + str(language) + ', 1200','END','END']
        (folder / 'version.rc').write_text('\n'.join(rc) + '\n'); run(label + '-rc', [prefix / 'bin/llvm-rc.exe', '-fo', folder / 'version.res', folder / 'version.rc'])
        args = ['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"' + (here / 'inputs/Microsoft.snk').as_posix() + '"','/out:"' + (folder / (name + '.dll')).as_posix() + '"','/win32res:"' + (folder / 'version.res').as_posix() + '"','/runtimeMetadataVersion:v4.0.30319']
        args += ['/reference:"' + p.as_posix() + '"' for p in refs] + ['"' + p.as_posix() + '"' for p in sources]
        rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n'); run(label, [prefix / 'lib/dotnet/dotnet.exe', compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
        records[label] = dict(source_compiler_input_sha256={p.as_posix():sha(p) for p in sources}, reference_sha256={p.as_posix():sha(p) for p in refs}, original_framework=tfm)
        print('PASS original source reference compilation:', label, flush=True)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, profiles=records, original_source_sha256=original_hashes, original_files_edited_in_place=0, runtime_implementations_supplied=False, full_dependency_goal_complete=False), indent=2) + '\n')
