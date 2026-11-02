"""Extract the pinned Roslyn source with native Python, removing executable inputs."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile

archive,out=map(Path,sys.argv[1:]);source=out/'roslyn-source';assert not source.exists();source.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
files={};removed=[]
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2];p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
        data=t.extractfile(m).read();digest=hashlib.sha256(data).hexdigest()
        if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip','.winmd','.a','.so','.o'} or data[:2]==b'MZ':
            removed.append(dict(path=name,sha256=digest));continue
        dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);files[name]=digest
(out/'extracted-source-inputs.json').write_text(json.dumps(dict(original_file_sha256=files,removed_binary_inputs=removed),indent=2)+'\n')
print('PASS pinned Roslyn source extraction:',len(files),'original files;',len(removed),'binary inputs removed')
