"""Materialize the exact Asn1 8.0.1 production/shared sources without binary fixtures."""
from pathlib import Path
import gzip,hashlib,io,json,sys,tarfile
archive,out,bundle=(Path(p).resolve() for p in sys.argv[1:]);assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2814c6b2933deaa6f3f950eb4ce797a9155e3ab103133061a1d73f0afd2a0a18';out.mkdir();source=out/'runtime';source.mkdir();prefix='runtime-2aade6beb02ea367fd97c4070a4198802fe61c03/';dirs=['src/libraries/System.Formats.Asn1/','src/libraries/Common/','src/libraries/System.Private.CoreLib/src/','eng/'];roots=['global.json','Directory.Build.props','Directory.Build.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props'];records={};excluded=[]
with tarfile.open(archive,'r|gz') as t:
 for m in t:
  assert m.name.startswith(prefix.rstrip('/'))
  rel=m.name[len(prefix):]
  if not m.isfile() or not (rel in roots or any(rel.startswith(d) for d in dirs)):continue
  data=t.extractfile(m).read()
  if Path(rel).suffix.lower() in ['.dll','.exe','.pdb','.nupkg','.snk','.lib','.obj','.a','.winmd']:
   excluded.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest()));continue
  p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[rel]=dict(sha256=hashlib.sha256(data).hexdigest(),git_blob_sha1=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest())
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='2aade6beb02ea367fd97c4070a4198802fe61c03',source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=records,excluded_binary_fixtures=excluded,original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n')
with bundle.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as z,tarfile.open(fileobj=z,mode='w') as t:
 for p in sorted(out.rglob('*')):
  if p.is_file():
   data=p.read_bytes();info=tarfile.TarInfo(p.relative_to(out).as_posix());info.size=len(data);info.mode=0o644;t.addfile(info,io.BytesIO(data))
print('PASS',len(records),'original source files; bundle',hashlib.sha256(bundle.read_bytes()).hexdigest())
