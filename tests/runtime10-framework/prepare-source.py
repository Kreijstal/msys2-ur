"""Materialize pristine managed-framework sources from the pinned runtime archive."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile

root=Path(sys.argv[1]).resolve();archive=root/'runtime-v10.0.5.tar.gz'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
source=root/'r';assert not source.exists(),source
source.mkdir();inputs={}
with tarfile.open(archive) as tar:
 assert tar.pax_headers['comment']=='081d220c0a773ffb7c6bea6b48727833576a65ef'
 for member in tar:
  relative=member.name.partition('/')[2]
  if not member.isfile():continue
  if not (relative.startswith(('src/libraries/','src/tools/illink/src/ILLink.Tasks/','eng/')) or '/' not in relative):continue
  assert '..' not in PurePosixPath(relative).parts and not relative.startswith('/')
  file=source/relative;file.parent.mkdir(parents=True,exist_ok=True)
  data=tar.extractfile(member).read();file.write_bytes(data)
  inputs[relative]=hashlib.sha256(data).hexdigest()
arcade=root/'arcade-runtime10-4bf37ce6.tar.gz'
assert sha(arcade)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
with tarfile.open(arcade) as tar:
 for member in tar:
  if member.name.partition('/')[2]=='LICENSE.TXT':
   (root/'Arcade-LICENSE.TXT').write_bytes(tar.extractfile(member).read())
(root/'managed-source-inputs.json').write_text(json.dumps(dict(
 runtime_commit='081d220c0a773ffb7c6bea6b48727833576a65ef',
 archive_sha256=sha(archive),pristine_materialized_files=inputs,
 original_source_changes=0),indent=2)+'\n')
print('PASS pristine framework source extraction:',len(inputs),'pinned archive files')
