"""Compile three original Reflection reference profiles."""
from pathlib import Path
import hashlib
import json
import re
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
profiles = [('System.Reflection', 'netstandard1.0'), ('System.Reflection', 'netstandard1.3'), ('System.Reflection', 'netstandard1.5')]
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
        selected = {}
        for ident in sorted(closure):
            depname, version = ident.split('/')
            if depname not in selected or tuple(map(int, version.split('.'))) > tuple(map(int, selected[depname].split('/')[1].split('.'))): selected[depname] = ident
        refs = [prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / ident / (ident.split('/')[0] + '.dll') for ident in sorted(selected.values())]
        assert all(p.is_file() for p in refs)
        folder = out / 'raw' / name / framework; folder.mkdir(parents=True)
        args = ['/nostdlib+', '/target:library', '/refonly', '/unsafe+', '/nullable:disable', '/langversion:latest', '/optimize+',
            '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+', '/keyfile:"' + key.as_posix() + '"',
            '/out:"' + (folder / (name + '.dll')).as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
        if framework == 'netstandard1.3':
            versions = json.loads((here / 'inputs/reference-data.json').read_text())
            native_version = next(v['native_version'] for v in versions if '/netstandard1.3/' in v['file'])
            rc = ['LANGUAGE 9,1', '1 VERSIONINFO', 'FILEVERSION ' + ','.join(re.findall(r'\d+', native_version['FileVersion'])[:4]),
                  'PRODUCTVERSION ' + ','.join(re.findall(r'\d+', native_version['ProductVersion'])[:4]), 'FILEFLAGSMASK 0x3f', 'FILEFLAGS 0', 'FILEOS 4', 'FILETYPE 2', 'FILESUBTYPE 0',
                  'BEGIN', 'BLOCK "StringFileInfo"', 'BEGIN', 'BLOCK "040904b0"', 'BEGIN']
            for field in ['CompanyName', 'FileDescription', 'FileVersion', 'InternalName', 'LegalCopyright', 'LegalTrademarks', 'OriginalFilename', 'ProductName', 'ProductVersion']:
                rc.append('VALUE ' + json.dumps(field) + ', L' + json.dumps(native_version[field], ensure_ascii=True).replace('\\u', '\\x'))
            rc += ['END', 'END', 'BLOCK "VarFileInfo"', 'BEGIN', 'VALUE "Translation", 1033, 1200', 'END', 'END']
            resource = folder / 'version.rc'; resource.write_text('\n'.join(rc) + '\n')
            run(name + '-' + framework + '-native-version', [prefix / 'bin/llvm-rc.exe', '-fo', folder / 'version.res', resource])
            args.append('/win32res:"' + (folder / 'version.res').as_posix() + '"')
        args += ['/reference:"' + p.as_posix() + '"' for p in refs] + ['"' + source.as_posix() + '"']
        rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
        run(name + '-' + framework, [prefix / 'lib/dotnet/dotnet.exe', compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
        records[name + '/' + framework] = dict(original_source=original, source_sha256=sha(source),
            source_reference_hashes={p.as_posix(): sha(p) for p in refs}, reference_only=True)
        print('PASS original source reference compilation:', name, framework, flush=True)
(out / 'results.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive), profiles=records, commands=commands, original_source_changes=0, runtime_facade_built=False), indent=2) + '\n')
