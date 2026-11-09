"""Packaging-only maintenance of a pinned published Qt WebEngine payload."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import subprocess
import sys
import tarfile

mode, archive_name, output_name, prefix, package = sys.argv[1:]
archive, output = Path(archive_name).resolve(), Path(output_name)
assert prefix in ('clang64', 'ucrt64')
assert package == 'mingw-w64-' + ('clang-x86_64' if prefix == 'clang64' else 'ucrt-x86_64') + '-qt6-webengine'
sha = lambda data: hashlib.sha256(data).hexdigest()

def inspect(extract=False):
    files, metadata, removed = {}, {}, {}
    process = subprocess.Popen(['zstd', '-dc', str(archive)], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
            for member in tar:
                name = member.name.removeprefix('./')
                path = PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts, name
                assert member.isfile() or member.isdir(), ('Unsupported archive member', name)
                if member.isdir():
                    continue
                data = tar.extractfile(member).read()
                if name in ('.PKGINFO', '.BUILDINFO', '.MTREE'):
                    metadata[name] = data
                    continue
                assert path.parts[0] == prefix, name
                record = {'sha256': sha(data), 'size': len(data), 'mode': member.mode}
                if name.endswith('.debug'):
                    removed[name] = record
                    continue
                files[name] = record
                if extract:
                    target = output / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    os.chmod(target, member.mode)
        process.stdout.read()
    finally:
        process.stdout.close()
    assert process.wait() == 0
    return files, metadata, removed

files, metadata, removed = inspect(extract=mode == 'prepare')
assert all(key in metadata for key in ('.PKGINFO', '.BUILDINFO', '.MTREE'))
info = {}
for line in metadata['.PKGINFO'].decode().splitlines():
    if ' = ' in line:
        key, value = line.split(' = ', 1)
        info.setdefault(key, []).append(value)
assert info['pkgname'] == [package] and info['pkgver'] == ['6.11.2-2']
assert len(removed) == 9
manifest = output.parent / 'original-payload.json'
if mode == 'prepare':
    doc = output / prefix / 'share/doc/qt6-webengine/runtime-repack'
    assert not doc.exists()
    doc.mkdir(parents=True)
    (doc / 'original.BUILDINFO').write_bytes(metadata['.BUILDINFO'])
    (doc / 'original.PKGINFO').write_bytes(metadata['.PKGINFO'])
    provenance = {'operation': 'Packaging-only rebuild; compiled runtime payload unchanged',
                  'source_package': archive.name, 'source_package_sha256': sha(archive.read_bytes()),
                  'source_version': '6.11.2-2', 'new_version': '6.11.2-3',
                  'removed_debug_files': removed, 'retained_payload_files': len(files),
                  'source_buildinfo_sha256': sha(metadata['.BUILDINFO']),
                  'debug_symbols_regenerated': False}
    (doc / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    manifest.write_text(json.dumps({'retained_files': files, 'source_metadata': info}, indent=2) + '\n')
elif mode == 'check':
    assert json.loads(manifest.read_text())['retained_files'] == files
    for name, entry in files.items():
        target = output / name
        assert target.is_file() and sha(target.read_bytes()) == entry['sha256'], name
    assert not list(output.rglob('*.debug'))
else:
    raise ValueError(mode)
print('PASS', mode, len(files), 'original payload files;', len(removed), 'debug companions excluded')
