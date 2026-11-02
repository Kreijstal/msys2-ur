"""Materialize SDK-pinned runtime support trees and verify VMR git blob identities."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,shutil,sys,urllib.request
base,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();shutil.copytree(base,out/'runtime');source=out/'runtime';commit='44525024595742ebe09023abe709df51de65009b';api='https://api.github.com/repos/dotnet/dotnet';raw=f'https://raw.githubusercontent.com/dotnet/dotnet/{commit}/src/runtime/'
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-package-builder'}),timeout=60) as r:return r.read()
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
dirs=['src/libraries/System.IO.Hashing','src/libraries/Microsoft.Extensions.DependencyModel','src/installer/managed/Microsoft.NET.HostModel','src/libraries/Common','src/coreclr/tools/Common/Compiler/Win32Resources']
records={};changes=[];skipped=[]
for rel in dirs:
    entries=json.loads(get(f'{api}/contents/src/runtime/{rel}?ref={commit}'))
    # contents returns the directory's entries; obtain its tree via the first entry's parent listing.
    parent,name=rel.rsplit('/',1);siblings=json.loads(get(f'{api}/contents/src/runtime/{parent}?ref={commit}'));entry=next(e for e in siblings if e['name']==name)
    tree=json.loads(get(entry['git_url']+'?recursive=1'))['tree']
    current={rel+'/'+e['path']:e for e in tree if e['type']=='blob'}
    def materialize(item):
        path,e=item;target=source/path
        if target.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.lib','.obj','.a','.winmd','.snk'}:return path,None,'skip'
        old=target.read_bytes() if target.exists() else None
        if old is None or gitsha(old)!=e['sha']:
            data=get(raw+path);assert gitsha(data)==e['sha'],path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            return path,dict(git_blob_sha1=e['sha'],sha256=hashlib.sha256(data).hexdigest()),dict(path=path,baseline_present=old is not None,baseline_sha256=hashlib.sha256(old).hexdigest() if old is not None else None,vmr_sha256=hashlib.sha256(data).hexdigest())
        return path,dict(git_blob_sha1=e['sha'],sha256=hashlib.sha256(old).hexdigest()),None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path,record,change in pool.map(materialize,current.items()):
            if record:records[path]=record
            if change=='skip':skipped.append(path)
            elif change:changes.append(change)
    for p in (source/rel).rglob('*'):
        if p.is_file() and p.relative_to(source).as_posix() not in current:p.unlink()
    print('Verified VMR tree',rel,len(current),'blobs',flush=True)
for rel in ['Directory.Build.props','Directory.Build.targets','eng/Versions.props','eng/Version.Details.props','eng/Version.Details.xml','src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets','src/libraries/System.Private.CoreLib/src/System/Numerics/Hashing/HashHelpers.cs','src/coreclr/tools/Common/System/Collections/Generic/ArrayBuilder.cs']:
    data=get(raw+rel);target=source/rel;old=target.read_bytes() if target.exists() else None
    if old!=data:changes.append(dict(path=rel,baseline_present=old is not None,baseline_sha256=hashlib.sha256(old).hexdigest() if old is not None else None,vmr_sha256=hashlib.sha256(data).hexdigest()))
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);records[rel]=dict(git_blob_sha1=gitsha(data),sha256=hashlib.sha256(data).hexdigest())
(out/'vmr-source-inputs.json').write_text(json.dumps(dict(vmr_commit=commit,mapped_runtime_commit='9ffface2f3fa6fbbb427793c3230b1626a1fdd84',original_vmr_files=records,changes_from_mapped_archive=changes,excluded_binary_fixtures=skipped,original_production_source_changes_by_us=0),indent=2)+'\n');print('PASS verified',len(records),'VMR source files;',len(changes),'upstream-to-VMR differences')
