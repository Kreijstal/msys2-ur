"""Compare original PE resource data and native versions without loading code."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

archives, producer, out, prefix, reader = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir()
pairs = []
aliases = {}
for name, version in [('System.Collections.Immutable', '1.5.0'), ('System.Reflection.Metadata', '1.6.0')]:
    with zipfile.ZipFile(archives / (name.lower() + '.' + version + '.metadata-only.nupkg')) as z:
        paths = [n for n in z.namelist() if n.startswith('lib/netstandard') and n.endswith('.dll')]
        for member in paths:
            framework = member.split('/')[1]
            path = out / 'metadata-only' / name / framework / (name + '.dll')
            path.parent.mkdir(parents=True); path.write_bytes(z.read(member))
            candidate = producer / name / framework / 'bin/Release' / (name + '.dll')
            pairs.append((name + '/' + framework, path, candidate))
        portable = next(n for n in z.namelist() if n.startswith('lib/portable-') and n.endswith('.dll'))
        standard = 'netstandard1.0' if name.endswith('Immutable') else 'netstandard1.1'
        assert z.read(portable) == z.read('lib/' + standard + '/' + name + '.dll')
        aliases[name] = dict(original_portable_path=portable, original_alias_framework=standard, original_DLL_byte_alias_verified=True)
dotnet = prefix / 'lib/dotnet/dotnet.exe'; commands = []
def read(label, paths):
    command = [str(dotnet), str(reader), *[str(p) for p in paths]]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.json')).write_bytes(result.stdout)
    commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, result.stdout.decode('utf-8', errors='replace')
    return json.loads(result.stdout)
before = read('original', [p[1] for p in pairs]); after = read('candidate', [p[2] for p in pairs])
assert len(before) == len(after) == 5
results = {}
for (profile, _, candidate), expected, actual in zip(pairs, before, after):
    for key in ['name', 'version', 'public_key', 'public_key_token', 'attributes', 'resources', 'embedded_nonresource_blob_hashes', 'exported_types', 'references', 'native_version']:
        assert actual[key] == expected[key], (profile, key)
    assert candidate.with_suffix('.pdb').read_bytes()[:4] == b'BSJB'
    results[profile] = dict(resource_strings=sum(len(v) for v in actual['resources'].values()),
        original_managed_and_native_versions_and_resources_equal=True, fresh_source_portable_PDB_present=True)
    print('PASS original resource values, native/managed versions and public-key data:', profile)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, profiles=results, original_portable_aliases=aliases,
    original_assemblies_executed=False), indent=2) + '\n')
