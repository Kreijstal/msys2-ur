"""Extract original NET6 contracts and shared policy for exact Pkcs6/Asn1 prerequisites."""
from pathlib import Path
import gzip, hashlib, io, json, sys, tarfile

archive, out, bundle = (Path(p).resolve() for p in sys.argv[1:])
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == '82b6d848c062c90b6773e0ebed0692be6468503bea3ca0d9bfcb95d727879ea2'
out.mkdir()
root = out / 'runtime'
root.mkdir()
prefix = 'runtime-e37fab9fc9f7bce120a7165491ed392a73f8ab51/'
records = {}
with tarfile.open(archive) as t:
    for m in t:
        if not m.isfile():
            continue
        assert m.name.startswith(prefix)
        rel = m.name[len(prefix):]
        parts = Path(rel).parts
        wanted = (rel in ['Directory.Build.props', 'Directory.Build.targets', 'LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT']
            or rel.startswith(('eng/', 'src/libraries/Common/', 'src/libraries/System.Private.CoreLib/src/', 'src/libraries/shims/'))
            or (len(parts) >= 4 and parts[:2] == ('src', 'libraries') and parts[3] == 'ref')
            or (rel.startswith('src/libraries/') and Path(rel).suffix in {'.props', '.targets'} and 'tests' not in parts))
        if not wanted or Path(rel).suffix.lower() in ['.dll', '.exe', '.pdb', '.nupkg', '.snk', '.lib', '.obj', '.a', '.winmd']:
            continue
        data = t.extractfile(m).read()
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        records[rel] = hashlib.sha256(data).hexdigest()
manifest = dict(source_commit='e37fab9fc9f7bce120a7165491ed392a73f8ab51', runtime_version='6.0.19',
    source_archive_sha256=digest, files=records, original_production_source_changes=0,
    compiled=False, full_dependency_goal_complete=False)
(out / 'source-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
with bundle.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode='w') as t:
    for f in sorted(out.rglob('*')):
        if f.is_file():
            data = f.read_bytes()
            m = tarfile.TarInfo(f.relative_to(out).as_posix())
            m.size = len(data)
            m.mode = 0o644
            t.addfile(m, io.BytesIO(data))
print('PASS', len(records), 'original source files; snapshot', hashlib.sha256(bundle.read_bytes()).hexdigest())
