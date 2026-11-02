"""Extract the pinned original analyzer sources; exclude binary test fixtures."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import sys
import tarfile

archive, output, bundle = (Path(p).resolve() for p in sys.argv[1:])
commit = '22ea6422f85b05ca0793cc3b76375487be407f5d'
archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
assert archive_hash == '49a992347546aef48cb31673b294bd1b10c30e68bbb53be61d411bb0d7219e1e'
output.mkdir()
source = output / 'source'
source.mkdir()
prefix = 'roslyn-analyzers-' + commit + '/'
directories = ['eng/', 'src/PublicApiAnalyzers/', 'src/Utilities/',
               'src/Roslyn.Diagnostics.Analyzers/Core/',
               'nuget/PerformanceSensitiveAnalyzers/', 'nuget/PublicApiAnalyzers/']
root_files = ['src/Directory.Build.props']
records = {}
with tarfile.open(archive, 'r|gz') as source_archive:
    for member in source_archive:
        if not member.isfile():
            continue
        assert member.name.startswith(prefix), member.name
        relative = member.name[len(prefix):]
        if not ('/' not in relative or relative in root_files or
                any(relative.startswith(p) for p in directories)):
            continue
        if Path(relative).suffix.lower() in {'.dll', '.exe', '.pdb', '.nupkg', '.snk', '.lib', '.obj', '.a', '.winmd'}:
            continue
        data = source_archive.extractfile(member).read()
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records[relative] = hashlib.sha256(data).hexdigest()
ordered = dict(sorted((k, v) for k, v in records.items() if k != 'src/Directory.Build.props'))
ordered['src/Directory.Build.props'] = records['src/Directory.Build.props']
manifest = dict(commit=commit, source_archive_sha256=archive_hash, files=ordered)
(output / 'source-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
with bundle.open('wb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', mtime=0, filename='') as compressed:
    with tarfile.open(fileobj=compressed, mode='w') as snapshot:
        for path in sorted(output.rglob('*'), key=lambda p:p.relative_to(output).parts):
            if path.is_file():
                data = path.read_bytes()
                info = tarfile.TarInfo(path.relative_to(output).as_posix())
                info.size = len(data)
                info.mode = 0o644
                snapshot.addfile(info, io.BytesIO(data))
print(len(records), 'original files;', hashlib.sha256(bundle.read_bytes()).hexdigest())
