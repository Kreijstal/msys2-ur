"""Verify the complete checkout against the original Git tree and signed commit."""
from pathlib import Path
import hashlib,json,sys

here=Path(__file__).resolve().parent
lock=json.loads((here/'source-inputs.json').read_text())
def git_hash(kind,data):return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()
commit=(here/'upstream-commit.txt').read_bytes()
assert hashlib.sha256(commit).hexdigest()==lock['upstream_commit_sha256']
assert git_hash('commit',commit)==lock['commit']
assert commit.splitlines()[0]==('tree '+lock['tree']).encode()
root=Path(sys.argv[1]).resolve();executable=set(lock['executable_files']);files=[]
def tree(folder):
 children=[]
 for path in folder.iterdir():
  if path.name=='.git':continue
  assert not path.is_symlink(),path
  relative=path.relative_to(root).as_posix()
  if path.is_dir():kind='40000';sha=tree(path);sort=path.name.encode()+b'/'
  else:
   kind='100755' if relative in executable else '100644'
   sha=git_hash('blob',path.read_bytes());files.append(relative);sort=path.name.encode()
  children.append((sort,kind,path.name,sha))
 payload=b''.join((mode+' '+name).encode()+b'\0'+bytes.fromhex(sha) for _,mode,name,sha in sorted(children))
 return git_hash('tree',payload)
actual=tree(root)
assert actual==lock['tree'],(actual,lock['tree'])
assert len(files)==lock['source_files'] and executable.issubset(files)
print('PASS all',len(files),'source files, exact Git tree',actual,'and original signed commit',lock['commit'])
