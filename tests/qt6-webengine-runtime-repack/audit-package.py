"""Independently compare old/new pacman artifacts; no Qt code is executed."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import sys
import tarfile

old, new, output = map(Path, sys.argv[1:])

def contents(archive):
    payload, metadata = {}, {}
    process = subprocess.Popen(['zstd', '-dc', str(archive.resolve())], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
            for entry in tar:
                name = entry.name.removeprefix('./')
                if entry.isdir():
                    continue
                assert entry.isfile(), name
                data = tar.extractfile(entry).read()
                if name.startswith('.'):
                    metadata[name] = data
                else:
                    payload[name] = {'sha256': hashlib.sha256(data).hexdigest(),
                                     'size': len(data), 'mode': entry.mode}
        process.stdout.read()
    finally:
        process.stdout.close()
    assert process.wait() == 0
    return payload, metadata

def info(data):
    result = {}
    for line in data.decode().splitlines():
        if ' = ' in line:
            key, value = line.split(' = ', 1)
            result.setdefault(key, []).append(value)
    return result

before, old_meta = contents(old)
after, new_meta = contents(new)
a, b = info(old_meta['.PKGINFO']), info(new_meta['.PKGINFO'])
assert a['pkgver'] == ['6.11.2-2'] and b['pkgver'] == ['6.11.2-3']
for key in ['pkgname', 'arch', 'pkgdesc', 'url', 'license', 'group', 'depend']:
    assert a.get(key) == b.get(key), key
removed = {name: value for name, value in before.items() if name.endswith('.debug')}
assert len(removed) == 9 and not any(name.endswith('.debug') for name in after)
expected = {name: value for name, value in before.items() if name not in removed}
assert all(after.get(name) == record for name, record in expected.items())
prefix = next(iter(before)).split('/')[0]
doc = prefix + '/share/doc/qt6-webengine/runtime-repack/'
assert set(after) - set(expected) == {doc + name for name in ['original.BUILDINFO', 'original.PKGINFO', 'provenance.json']}
for name in ['BUILDINFO', 'PKGINFO']:
    assert after[doc + 'original.' + name]['sha256'] == hashlib.sha256(old_meta['.' + name]).hexdigest()
assert info(new_meta['.BUILDINFO'])['pkgver'] == ['6.11.2-3']
recipe = Path(__file__).resolve().parents[2] / 'mingw-w64-qt6-webengine-runtime-repack/PKGBUILD'
assert info(new_meta['.BUILDINFO'])['pkgbuild_sha256sum'] == [hashlib.sha256(recipe.read_bytes()).hexdigest()]
assert "options=('!strip' '!debug' '!lto')" in recipe.read_text()
# BUILDINFO records makepkg.conf defaults; recipe-level overrides are in the hash-bound PKGBUILD.
mtree = gzip.decompress(new_meta['.MTREE']).decode()
assert '.debug ' not in mtree and 'Qt6WebEngineCore.debug' not in mtree
assert 'Qt6WebEngineCore.dll' in mtree
report = {'passed': True, 'old_archive': old.name, 'new_archive': new.name,
          'old_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
          'new_sha256': hashlib.sha256(new.read_bytes()).hexdigest(),
          'new_archive_bytes': new.stat().st_size, 'compiled_runtime_rebuilt': False,
          'all_retained_payload_bytes_and_modes_unchanged': True,
          'dependencies_and_licenses_unchanged': True,
          'retained_payload_files': len(expected), 'removed_debug_files': removed,
          'uncompressed_debug_bytes_removed': sum(v['size'] for v in removed.values()),
          'new_package_info': b, 'new_build_info': info(new_meta['.BUILDINFO']),
          'all_payload_files': after}
output.write_text(json.dumps(report, indent=2) + '\n')
print('PASS', b['pkgname'][0], len(expected), 'unchanged payload files;', len(removed), 'debug files excluded; regenerated metadata verified')
