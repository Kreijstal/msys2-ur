"""Extract the complete pinned Azure.Identity component and original build metadata."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:]);digest=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
assert digest.hexdigest()=='b7cece1f00f7f6e5c2409bc41bcdc5b9fbf1b005af65d9cc5115bdf045bd66a2'
out.mkdir()
metadata={'LICENSE.txt','NOTICE.txt','Directory.Build.props','Directory.Build.targets',
          'sdk/Directory.Build.props','sdk/Directory.Build.targets','sdk/core/Directory.Build.props','sdk/core/Directory.Build.targets',
          'eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','eng/AzureSDKClient.snk'}
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        prefix,path=member.name.split('/',1)
        assert prefix=='azure-sdk-for-net-2856f9a00d6cb96f71b724d29b1ce8ce271c4137'
        assert '..' not in Path(path).parts
        if path.startswith('sdk/identity/Azure.Identity/') or path.startswith('sdk/core/Azure.Core/src/Shared/') or path in metadata:
            target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
print('PASS full pinned Azure archive and complete Azure.Identity component/build metadata extraction')
