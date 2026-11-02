"""Extract the pinned Roslyn source with native Python, removing executable inputs."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile

archive,out=map(Path,sys.argv[1:]);source=out/'roslyn-source';assert not source.exists();source.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c'
files={};removed=[]
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b'
    for m in t:
        if not m.isfile():continue
        name=m.name.partition('/')[2];p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
        data=t.extractfile(m).read();digest=hashlib.sha256(data).hexdigest()
        if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip','.winmd','.a','.so','.o'} or data[:2]==b'MZ':
            removed.append(dict(path=name,sha256=digest));continue
        dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);files[name]=digest
(out/'extracted-source-inputs.json').write_text(json.dumps(dict(original_file_sha256=files,removed_binary_inputs=removed),indent=2)+'\n')
print('PASS pinned Roslyn source extraction:',len(files),'original files;',len(removed),'binary inputs removed')
