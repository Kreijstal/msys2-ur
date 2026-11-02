"""Acquire the SDK-pinned VMR Extensions source closure with Git blob verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,sys,tarfile,urllib.parse,urllib.request
out=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=True);source=out/'runtime';source.mkdir(exist_ok=True)
commit='44525024595742ebe09023abe709df51de65009b';raw=f'https://raw.githubusercontent.com/dotnet/dotnet/{commit}/src/runtime/';api='https://api.github.com/repos/dotnet/dotnet';blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
names=['Microsoft.Extensions.Primitives','Microsoft.Extensions.DependencyInjection.Abstractions','Microsoft.Extensions.DependencyInjection','Microsoft.Extensions.Logging.Abstractions','Microsoft.Extensions.Logging','Microsoft.Extensions.Logging.Configuration','Microsoft.Extensions.Logging.Console','Microsoft.Extensions.Configuration.Abstractions','Microsoft.Extensions.Configuration','Microsoft.Extensions.Configuration.Binder','Microsoft.Extensions.Options','Microsoft.Extensions.Options.ConfigurationExtensions','Microsoft.Extensions.FileSystemGlobbing','System.Diagnostics.DiagnosticSource','System.ServiceProcess.ServiceController']
dirs=['src/libraries/'+n for n in names]+['src/libraries/Common','src/libraries/System.Private.CoreLib/src','eng']
roots=['Directory.Build.props','Directory.Build.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/NetCoreAppLibrary.props']
archive=Path('/tmp/dotnet10-sources/runtime-sdk10-9ffface2.tar.gz')
with tarfile.open(archive) as t:
 for m in t:
  rel=m.name.partition('/')[2]
  if m.isfile() and (any(rel.startswith(d+'/') for d in dirs) or rel in roots):
   if (source/rel).exists():continue
   if Path(rel).suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.snk','.lib','.obj','.a','.winmd'}:continue
   p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-package-builder'}),timeout=60).read()
records={};changes=[];skipped=[];listings={}
for rel in dirs:
 parent,name=rel.rsplit('/',1) if '/' in rel else ('',rel)
 if parent not in listings:listings[parent]=json.loads(get(f'{api}/contents/src/runtime'+('/'+parent if parent else '')+f'?ref={commit}'))
 entry=next(e for e in listings[parent] if e['name']==name);assert entry['url'].endswith('?ref='+commit),entry;tree=json.loads(get(entry['git_url']+'?recursive=1'));assert not tree.get('truncated')
 current={rel+'/'+e['path']:e for e in tree['tree'] if e['type']=='blob'}
 def fetch(item):
  path,e=item;p=source/path
  if p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.snk','.lib','.obj','.a','.winmd'}:return path,None,None
  original=p.read_bytes() if p.exists() else None;data=original
  if data is None or blob(data)!=e['sha']:
   try:data=get(raw+urllib.parse.quote(path,safe='/'))
   except Exception as error:raise RuntimeError(path) from error
  assert blob(data)==e['sha'],path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  return path,dict(git_blob_sha1=e['sha'],sha256=hashlib.sha256(data).hexdigest()),original!=data
 with ThreadPoolExecutor(max_workers=4) as pool:
  for path,r,changed in pool.map(fetch,current.items()):
   if r:records[path]=r
   else:skipped.append(path)
   if changed:changes.append(path)
 for p in (source/rel).rglob('*'):
  if p.is_file() and p.relative_to(source).as_posix() not in current:p.unlink()
 print('Verified',rel,len(current),'Git blobs',flush=True)
for rel in roots:
 data=get(raw+rel);p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[rel]=dict(git_blob_sha1=blob(data),sha256=hashlib.sha256(data).hexdigest())
(out/'source-inputs.json').write_text(json.dumps(dict(vmr_commit=commit,mapped_runtime_commit='9ffface2f3fa6fbbb427793c3230b1626a1fdd84',files=records,VMR_differences_from_mapped_archive=changes,excluded_binary_fixtures=skipped,original_production_source_changes_by_us=0,library_roots=names,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(records),'VMR files verified')
