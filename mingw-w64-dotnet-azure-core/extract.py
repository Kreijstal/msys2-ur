"""Extract the complete pinned Azure.Core component and original build metadata."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:]);digest=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
assert digest.hexdigest()=='f4e39501839027264cf5f5e8456c443376658b6030b15f6d18f4268520f1114f'
out.mkdir()
metadata={'LICENSE.txt','NOTICE.txt','Directory.Build.props','Directory.Build.targets',
          'sdk/Directory.Build.props','sdk/Directory.Build.targets','sdk/core/Directory.Build.props','sdk/core/Directory.Build.targets',
          'eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','eng/AzureSDKClient.snk'}
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        prefix,path=member.name.split('/',1)
        assert prefix=='azure-sdk-for-net-dae9516a40d0661a3351c3f6ddf0e0eb85ea2f6b'
        assert '..' not in Path(path).parts
        if path.startswith('sdk/core/Azure.Core/') or path in metadata:
            target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
print('PASS full pinned Azure archive and complete Azure.Core component/build metadata extraction')
