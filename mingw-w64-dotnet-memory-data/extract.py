"""Extract the complete pinned BinaryData component and original build metadata."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:]);digest=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
assert digest.hexdigest()=='a6cb4b058f24a49b8c62594723d171f8b782026fce5d7d0274c0282472189317'
out.mkdir()
metadata={'LICENSE.txt','NOTICE.txt','Directory.Build.props','Directory.Build.targets',
          'sdk/Directory.Build.props','sdk/Directory.Build.targets','sdk/core/Directory.Build.props','sdk/core/Directory.Build.targets',
          'eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets'}
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        prefix,path=member.name.split('/',1)
        assert prefix=='azure-sdk-for-net-7e3cf643977591e9041f4c628fd4d28237398e0b'
        assert '..' not in Path(path).parts
        if path.startswith('sdk/core/System.Memory.Data/') or path in metadata:
            target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
print('PASS full pinned Azure archive and complete BinaryData component/build metadata extraction')
