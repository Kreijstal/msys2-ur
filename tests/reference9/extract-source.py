"""Extract original runtime9 contracts and verify its exact Arcade task sources."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();source=root/'r';assert not source.exists();source.mkdir()
here=Path(__file__).resolve().parent;pins=json.loads((here/'source-pins.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
archive=root/'runtime-msbuild9-fa7cdded.tar.gz';assert sha(archive.read_bytes())==pins['runtime_archive_sha256']
files={};removed=[]
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']==pins['runtime_commit']
 for m in t:
  if not m.isfile():continue
  name=m.name.partition('/')[2];path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
  if not (name.startswith(('eng/','src/libraries/')) or '/' not in name):continue
  if 'tests' in path.parts or 'test' in path.parts:continue
  data=t.extractfile(m).read();digest=sha(data)
  if path.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip','.winmd','.a','.so','.o'} or data[:2]==b'MZ':removed.append(dict(path=name,sha256=digest));continue
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files[name]=digest
arcade=root/'arcade-runtime9-6666973b.tar.gz';assert sha(arcade.read_bytes())==pins['arcade_archive_sha256']
dep=E.parse(source/'eng/Version.Details.xml').find(".//Dependency[@Name='Microsoft.DotNet.Arcade.Sdk']");assert dep.findtext('Uri')=='https://github.com/dotnet/arcade' and dep.findtext('Sha')==pins['arcade_commit']
expected=json.loads((here/'inputs/arcade-source-inputs.json').read_text());verified={}
with tarfile.open(arcade) as t:
 assert t.pax_headers['comment']==pins['arcade_commit']
 wanted={v['source_path']:n for n,v in expected.items()}
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and rel=='LICENSE.TXT':(root/'Arcade-LICENSE.TXT').write_bytes(t.extractfile(m).read())
  if m.isfile() and rel in wanted:
   name=wanted[rel];data=t.extractfile(m).read();assert sha(data)==expected[name]['sha256'] and data==(here/'inputs'/name).read_bytes();verified[name]=sha(data)
assert set(verified)==set(expected)
(root/'source-extraction.json').write_text(json.dumps(dict(extracted_original_files=len(files),removed_binary_inputs=removed,source_file_sha256=files,arcade_source_commit=pins['arcade_commit'],arcade_original_tasks_verified=verified),indent=2)+'\n')
print('PASS pristine runtime9 extraction:',len(files),'files;',len(removed),'binary inputs removed;',len(verified),'exact Arcade inputs')
