from pathlib import Path
import hashlib,json,sys,tarfile
archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='8d2f0663d6e8d7d8bf478d4e14cf767d250851fe656be92ac26002524b11771d'
with tarfile.open(archive) as t:t.extractall(out,filter='data')
origin=json.loads((out/'source-inputs.json').read_text())
for rel,r in origin['files'].items():assert hashlib.sha256((out/rel).read_bytes()).hexdigest()==r['sha256'],rel
print('PASS exact immutable VMR source inputs',len(origin['files']))
