"""Extract pristine contract sources and prove original Arcade task provenance."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();source=root/'r';assert not source.exists();source.mkdir()
here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'runtime-v10.0.5.tar.gz';assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a'
files={};removed=[]
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='081d220c0a773ffb7c6bea6b48727833576a65ef'
 for m in t:
  if not m.isfile():continue
  name=m.name.partition('/')[2];path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
  if not (name.startswith(('eng/','src/libraries/')) or '/' not in name):continue
  if 'tests' in path.parts or 'test' in path.parts:continue
  data=t.extractfile(m).read();digest=hashlib.sha256(data).hexdigest()
  if path.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.res','.resources','.obj','.lib','.zip','.winmd','.a','.so','.o'} or data[:2]==b'MZ':removed.append(dict(path=name,sha256=digest));continue
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files[name]=digest
manifest=json.loads((here/'inputs/runtime10-vmr-source-manifest.json').read_text())
arcade=next(r for r in manifest['repositories'] if r['path']=='arcade')
assert arcade['commitSha']=='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d'
dep=E.parse(source/'eng/Version.Details.xml').find(".//Dependency[@Name='Microsoft.DotNet.Arcade.Sdk']")
assert dep.findtext('Uri')=='https://github.com/dotnet/dotnet' and dep.findtext('Sha')=='12f41dd0da1a94621e039e27aef264179c1104b5'
a=root/'arcade-runtime10-4bf37ce6.tar.gz';assert sha(a)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
expected=json.loads((here/'inputs/genfacades-source-inputs.json').read_text())
expected['CalculateAssemblyAndFileVersions.cs']=dict(vmr_path='src/arcade/src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs',sha256='7740ecad63add6b83cdca96b60ebb9c44ff4ece302833a8e5d2a9f43307cf0b7')
verified={}
with tarfile.open(a) as t:
 assert t.pax_headers['comment']==arcade['commitSha']
 wanted={item['vmr_path'].removeprefix('src/arcade/'):name for name,item in expected.items()}
 for m in t:
  relative=m.name.partition('/')[2]
  if relative=='LICENSE.TXT':(root/'Arcade-LICENSE.TXT').write_bytes(t.extractfile(m).read())
  if not m.isfile() or relative not in wanted:continue
  name=wanted[relative];data=t.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==expected[name]['sha256']
  assert data==(here/'inputs'/name).read_bytes();verified[name]=expected[name]['sha256']
assert verified.keys()==expected.keys()
(root/'source-extraction.json').write_text(json.dumps(dict(extracted_original_files=len(files),removed_binary_inputs=removed,source_file_sha256=files,arcade_source_commit=arcade['commitSha'],arcade_original_tasks_verified=verified),indent=2)+'\n')
print('PASS pristine runtime contract source extraction:',len(files),'files;',len(removed),'binary inputs removed; five exact original Arcade task/policy files')
