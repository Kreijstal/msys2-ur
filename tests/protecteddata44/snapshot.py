"""Extract exact CoreFX ProtectedData4.4.0 source/profile/shared inputs, excluding binary fixtures."""
from pathlib import Path
import gzip,hashlib,io,json,sys,tarfile
archive,out,bundle=(Path(p).resolve() for p in sys.argv[1:]);assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69';out.mkdir();source=out/'corefx';source.mkdir();prefix='corefx-8321c729934c0f8be754953439b88e6e1c120c24/';dirs=['src/System.Security.Cryptography.ProtectedData/','src/Common/','tools/','pkg/'];roots=['dir.props','dir.targets','src/dir.props','src/dir.targets','src/Directory.Build.props','src/Directory.Build.targets','dependencies.props','build-managed.proj','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'];records={}
with tarfile.open(archive) as t:
 for m in t:
  rel=m.name[len(prefix):]
  if not m.isfile() or not (rel in roots or any(rel.startswith(d) for d in dirs)):continue
  if Path(rel).suffix.lower() in ['.dll','.exe','.pdb','.nupkg','.snk','.lib','.obj','.a','.winmd']:continue
  data=t.extractfile(m).read();p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[rel]=hashlib.sha256(data).hexdigest()
(out/'source-inputs.json').write_text(json.dumps(dict(source_commit='8321c729934c0f8be754953439b88e6e1c120c24',archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=records,original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n')
with bundle.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as z,tarfile.open(fileobj=z,mode='w') as t:
 for p in sorted(out.rglob('*')):
  if p.is_file():
   data=p.read_bytes();info=tarfile.TarInfo(p.relative_to(out).as_posix());info.size=len(data);info.mode=0o644;t.addfile(info,io.BytesIO(data))
print('PASS',len(records),'original CoreFX files; source bundle',hashlib.sha256(bundle.read_bytes()).hexdigest())
