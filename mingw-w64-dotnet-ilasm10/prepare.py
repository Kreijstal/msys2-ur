"""Extract native runtime sources and apply the pinned ILAsm port without binaries."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

archive, root = (Path(p).resolve() for p in sys.argv[1:])
assert not root.exists(), root
root.mkdir(parents=True)
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
native = lambda p: subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
extract = r'''
from pathlib import Path, PurePosixPath
import hashlib,json,sys,tarfile
archive,root=map(Path,sys.argv[1:]);source=root/'r';source.mkdir();files={};removed=[];links=[]
prefixes=('eng/','src/coreclr/','src/native/')
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='081d220c0a773ffb7c6bea6b48727833576a65ef'
 for m in t:
  name=m.name.partition('/')[2]
  if not name or m.isdir():continue
  p=PurePosixPath(name);assert '..' not in p.parts and not p.is_absolute()
  if '/' in name and not name.startswith(prefixes):continue
  if m.issym():links.append((name,m.linkname));continue
  assert m.isfile(),name
  data=t.extractfile(m).read();digest=hashlib.sha256(data).hexdigest()
  if p.suffix.lower() in {'.dll','.exe','.so','.dylib','.nupkg','.a','.lib','.o','.obj','.winmd','.pdb','.resources','.wasm','.bc'} or data[:2]==b'MZ' or data[:4] in {b'\x7fELF',b'\x00asm',b'BC\xc0\xde'}:
   removed.append(dict(path=name,sha256=digest));continue
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files[name]=digest
 for name,link in links:
  p=source/name;target=(p.parent/link).resolve();assert target.is_relative_to(source) and target.is_file(),name
  p.write_bytes(target.read_bytes());files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(root/'source-inputs.json').write_text(json.dumps(dict(runtime_source_commit='081d220c0a773ffb7c6bea6b48727833576a65ef',runtime_archive_sha256='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a',original_file_sha256=files,removed_binary_inputs=removed,source_scope='Native CoreCLR/eng/native sources; managed libraries and tests are not build inputs',full_runtime10_built=False),indent=2)+'\n')
print('Extracted native source inputs:',len(files),'removed binaries:',len(removed),flush=True)
'''
subprocess.run(['/clang64/bin/python.exe', '-c', extract, native(archive), native(root)], check=True)
for patch_name in ['host-mingw.patch', 'coreclr-mingw.patch', 'resource-section-index.patch', 'cetcompat.patch']:
    patch = here / patch_name
    result = subprocess.run(['patch', '--forward', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-i', str(patch)],
                            cwd=root/'r', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (root/(patch_name+'.log')).write_text(result.stdout)
    assert result.returncode == 0, (patch_name, result.stdout)
for manifest in ['coreclr-port-source-inputs.json', 'port-source-inputs.json']:
    for path, item in json.loads((here/manifest).read_text())['changed_files'].items():
        assert sha(root/'r'/path) == item['ported_sha256'], path
(root/'patch-inputs.json').write_text(json.dumps({n: sha(here/n) for n in ['host-mingw.patch', 'coreclr-mingw.patch', 'resource-section-index.patch', 'cetcompat.patch']}, indent=2)+'\n')
print('PASS pinned native source and zero-fuzz host/CoreCLR/ILAsm port patches')
