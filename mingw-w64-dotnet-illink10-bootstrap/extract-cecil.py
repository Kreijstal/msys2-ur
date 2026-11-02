"""Extract exact pinned Cecil source with native Python, rejecting binary inputs."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile
archive,out=map(Path,sys.argv[1:]);assert not out.exists();out.mkdir();removed=[]
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3d82d4708f93dabd7442bcdb6f2667489fdd3ee2162d821b96d8aad62c33d019'
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='27abc57253a0d3010418e877fdfb35f9fa6806b9'
 for m in t:
  if not m.isfile():continue
  name=m.name.partition('/')[2];p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
  data=t.extractfile(m).read()
  if p.suffix.lower() in {'.exe','.dll','.pdb','.mdb','.nupkg','.zip'} or data[:2]==b'MZ':removed.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest()));continue
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
(out.parent/'removed-cecil-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
print('PASS original Cecil source extraction and binary rejection:',len(removed),'binary inputs removed')
