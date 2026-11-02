"""Acquire the original SDK-pinned VMR ASN.1 source and verified shared inputs."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,shutil,sys,tarfile,urllib.parse,urllib.request
base,mapped,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();source=out/'runtime';source.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();manifest=json.loads((base/'source-inputs.json').read_text());commit='44525024595742ebe09023abe709df51de65009b';assert manifest['vmr_commit']==commit;records={}
roots=['Directory.Build.props','Directory.Build.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props'];shared=['eng/','src/libraries/Common/','src/libraries/System.Private.CoreLib/src/']
for rel,meta in manifest['files'].items():
 if rel in roots or any(rel.startswith(p) for p in shared):
  src=base/'runtime'/rel;assert sha(src)==meta['sha256'],rel;dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);records[rel]=meta
library='src/libraries/System.Formats.Asn1';mapped_files={}
with tarfile.open(mapped) as t:
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and rel.startswith(library+'/'):mapped_files[rel]=t.extractfile(m).read()
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-build-packaging'}),timeout=60).read()
api='https://api.github.com/repos/dotnet/dotnet';parent=json.loads(get(f'{api}/contents/src/runtime/src/libraries?ref={commit}'));entry=next(e for e in parent if e['name']=='System.Formats.Asn1');assert entry['url'].endswith('?ref='+commit);tree=json.loads(get(entry['git_url']+'?recursive=1'));assert not tree.get('truncated');changes=[]
def fetch(e):
 rel=library+'/'+e['path'];data=mapped_files.get(rel)
 if data is None or blob(data)!=e['sha']:data=get(f'https://raw.githubusercontent.com/dotnet/dotnet/{commit}/src/runtime/'+urllib.parse.quote(rel,safe='/'))
 assert blob(data)==e['sha'],rel;p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return rel,dict(sha256=sha(p),git_blob_sha1=e['sha']),data!=mapped_files.get(rel)
with ThreadPoolExecutor(max_workers=4) as pool:
 for rel,meta,changed in pool.map(fetch,[e for e in tree['tree'] if e['type']=='blob']):
  records[rel]=meta
  if changed:changes.append(rel)
(out/'source-inputs.json').write_text(json.dumps(dict(vmr_commit=commit,mapped_runtime_commit='9ffface2f3fa6fbbb427793c3230b1626a1fdd84',mapped_archive_sha256=sha(mapped),files=records,VMR_changes_from_mapped_archive=changes,original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(records),'original VMR ASN.1/shared inputs,',len(changes),'mapped-to-VMR changes')
