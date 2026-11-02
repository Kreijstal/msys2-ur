"""Materialize the actual SDK-pinned VMR templating tree and verify every Git blob."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,sys,tarfile,urllib.parse,urllib.request
archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;policy=json.loads((here/'project-graph-20261029.json').read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==policy['source_archive_sha256'];commit=policy['vmr_commit'];api='https://api.github.com/repos/dotnet/dotnet';raw=f'https://raw.githubusercontent.com/dotnet/dotnet/{commit}/src/templating/'
with tarfile.open(archive) as t:t.extractall(out/'upstream',filter='data')
upstream=next((out/'upstream').iterdir());snapshot=out/'snapshot/templating';snapshot.mkdir(parents=True)
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-package-builder'}),timeout=60).read()
entries=json.loads(get(f'{api}/contents/src?ref={commit}'));entry=next(e for e in entries if e['name']=='templating');assert entry['url'].endswith('?ref='+commit);tree=json.loads(get(entry['git_url']+'?recursive=1'));assert not tree.get('truncated');blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();changed=[]
def fetch(e):
 rel=e['path'];original=(upstream/rel).read_bytes();data=original
 if blob(data)!=e['sha']:data=get(raw+urllib.parse.quote(rel,safe='/'))
 assert blob(data)==e['sha'],rel;p=snapshot/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 return rel,dict(git_blob_sha1=e['sha'],sha256=hashlib.sha256(data).hexdigest()),original!=data
records={}
with ThreadPoolExecutor(max_workers=4) as pool:
 for rel,meta,different in pool.map(fetch,[e for e in tree['tree'] if e['type']=='blob']):
  records[rel]=meta
  if different:changed.append(rel)
assert len(records)==1891
(out/'snapshot/source-inputs.json').write_text(json.dumps(dict(vmr_commit=commit,mapped_templating_commit=policy['mapped_templating_commit'],files=records,VMR_differences_from_mapped_archive=changed,original_production_source_changes_by_us=0,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS1891 actual VMR templating files; original project/policy/source differences preserved')
