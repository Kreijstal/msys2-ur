"""Build the three missing original Metadata1.6 NS1.1 reference contracts.

Reference assemblies are compiler inputs only. This does not provide legacy
runtime packages or substitute assemblies from a newer framework.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tarfile

archive, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
here = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
frameworks = {'System.IO.Compression': 'netstandard1.1', 'System.Reflection.Extensions': 'netstandard1.0',
              'System.Text.Encoding.Extensions': 'netstandard1.0'}
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
keys = {'b03f5f7f11d50a3a': (here / 'inputs/Microsoft.snk').read_bytes(),
        'b77a5c561934e089': bytes.fromhex('00000000000000000400000000000000')}
for token, data in keys.items():
    assert hashlib.sha1(data).digest()[-8:][::-1].hex() == token
    (out / (token + '.public.key')).write_bytes(data)
records = {}
with tarfile.open(archive) as tar:
    assert tar.pax_headers['comment'] == '5aeee2738338530a92d7f6caa2c7d5f569fed3c4'
    entries = {m.name.partition('/')[2]: m for m in tar if m.isfile()}
    for name, framework in frameworks.items():
        original = 'src/referencePackages/src/' + name.lower() + '/4.3.0/ref/' + framework + '/' + name + '.cs'
        source = out / 'source' / original; source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(tar.extractfile(entries[original]).read())
        baseline = json.loads((here / 'inputs' / (name + '-reference-metadata.json')).read_text())[name + '.dll']
        token = baseline['identity'].split('PublicKeyToken=')[1]
        closure = set()
        def select(key):
            if key in closure: return
            assert key in matrix, key
            closure.add(key)
            for ref in matrix[key]['references']:
                ident, version = ref.split(', Version='); select(ident + '/' + version.split(',')[0])
        for ref in baseline['references']:
            ident, version = ref.split(', Version='); select(ident + '/' + version.split(',')[0])
        refs = [prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / key / (key.split('/')[0] + '.dll') for key in sorted(closure)]
        assert all(p.is_file() for p in refs)
        folder = out / name; folder.mkdir()
        args = ['/nostdlib+', '/target:library', '/refonly', '/unsafe+', '/nullable:disable', '/langversion:latest',
                '/deterministic+', '/warnaserror+', '/nowarn:1701,1702', '/publicsign+',
                '/keyfile:"' + (out / (token + '.public.key')).as_posix() + '"',
                '/out:"' + (folder / (name + '.dll')).as_posix() + '"', '/runtimeMetadataVersion:v4.0.30319']
        args += ['/reference:"' + p.as_posix() + '"' for p in refs] + ['"' + source.as_posix() + '"']
        rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n')
        command = [str(prefix / 'lib/dotnet/dotnet.exe'), str(compiler / 'csc.dll'), '-noconfig', '@' + str(rsp)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (folder / 'compile.log').write_bytes(result.stdout)
        assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
        records[name] = dict(original_framework=framework, original_source=original, source_sha256=sha(source),
            reference_inputs={p.as_posix(): sha(p) for p in refs}, command=command, exit_code=result.returncode,
            DLL_sha256=sha(folder / (name + '.dll')), reference_only=True)
        print('PASS compiled original reference source', name, framework)
(out / 'results.json').write_text(json.dumps(dict(source_archive_sha256=sha(archive), libraries=records,
    original_sources_modified=0, original_assemblies_executed=False, full_metadata_validation_complete=False), indent=2) + '\n')
