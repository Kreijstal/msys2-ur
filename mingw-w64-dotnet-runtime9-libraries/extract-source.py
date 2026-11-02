"""Extract pinned original library sources with native Python and remove binary inputs."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys
import tarfile

archive,out=map(Path,sys.argv[1:]);source=out/'runtime-source';assert not source.exists();source.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def'
names=['System.Collections.Immutable','System.Reflection.Metadata','System.Composition.AttributedModel','System.Composition.Runtime','System.Composition.Hosting','System.Composition.Convention','System.Composition.TypedParts','Microsoft.Bcl.AsyncInterfaces','System.IO.Pipelines','System.Threading.Channels','System.Text.Encoding.CodePages','Common','System.Private.CoreLib','System.Runtime.InteropServices']
prefixes=tuple('src/libraries/'+n+'/' for n in names)+('eng/','src/libraries/System.Composition/')
root_files={'LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets'}
files={};removed=[];links=[]
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3'
    for m in t:
        name=m.name.partition('/')[2]
        if not name or m.isdir() or not (name.startswith(prefixes) or name in root_files):continue
        p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
        if m.issym():links.append((name,m.linkname));continue
        assert m.isfile(),name
        data=t.extractfile(m).read();digest=hashlib.sha256(data).hexdigest()
        if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.lib','.resources','.so','.a','.o','.winmd'} or data[:2]==b'MZ' or data[:4] in {b'\x7fELF',b'\x00asm',b'BC\xc0\xde'}:
            removed.append(dict(path=name,sha256=digest));continue
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);files[name]=digest
    for name,target in links:
        p=source/name;q=(p.parent/target).resolve();assert q.is_relative_to(source) and q.is_file(),name
        p.write_bytes(q.read_bytes());files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'extracted-source-inputs.json').write_text(json.dumps(dict(runtime_commit='9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3',original_file_sha256=files,removed_binary_inputs=removed),indent=2)+'\n')
print('PASS pinned source extraction:',len(files),'original files;',len(removed),'binary inputs removed')
