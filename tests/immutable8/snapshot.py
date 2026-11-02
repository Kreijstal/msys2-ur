"""Materialize the exact Immutable8.0.0 production/shared sources without binary fixtures."""
from pathlib import Path
import gzip,hashlib,io,json,sys,tarfile
archive,out,bundle=(Path(p).resolve() for p in sys.argv[1:]);assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3adbd0c8521e7594a8c112bca84e3e4753481111df8f6eba937f8b00d073f1cc';out.mkdir();source=out/'runtime';source.mkdir();prefix='runtime-5535e31a712343a63f5d7d796cd874e563e5ac14/';dirs=['src/libraries/System.Collections.Immutable/','src/libraries/Common/','src/libraries/System.Private.CoreLib/src/','eng/'];roots=['Directory.Build.props','Directory.Build.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props'];records={};excluded=[]
with tarfile.open(archive) as t:
 for m in t:
  assert m.name.startswith(prefix.rstrip('/'))
  rel=m.name[len(prefix):]
  if not m.isfile() or not (rel in roots or any(rel.startswith(d) for d in dirs)):continue
  data=t.extractfile(m).read()
  if Path(rel).suffix.lower() in ['.dll','.exe','.pdb','.nupkg','.snk','.lib','.obj','.a','.winmd']:
   excluded.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest()));continue
  p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[rel]=dict(sha256=hashlib.sha256(data).hexdigest(),git_blob_sha1=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest())
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='5535e31a712343a63f5d7d796cd874e563e5ac14',source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=records,excluded_binary_fixtures=excluded,original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n')
with bundle.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as z,tarfile.open(fileobj=z,mode='w') as t:
 for p in sorted(out.rglob('*')):
  if p.is_file():
   data=p.read_bytes();info=tarfile.TarInfo(p.relative_to(out).as_posix());info.size=len(data);info.mode=0o644;t.addfile(info,io.BytesIO(data))
print('PASS',len(records),'original source files; bundle',hashlib.sha256(bundle.read_bytes()).hexdigest())
