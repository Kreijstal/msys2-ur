"""Extract the complete pinned ClientModel component and original build metadata."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:]);digest=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
assert digest.hexdigest()=='bada24498a1e467f9c4ab1b4839b736d846a9b2a7b3dbed26b372fd93c6cfdc1'
out.mkdir()
metadata={'LICENSE.txt','NOTICE.txt','Directory.Build.props','Directory.Build.targets',
          'sdk/Directory.Build.props','sdk/Directory.Build.targets','sdk/core/Directory.Build.props','sdk/core/Directory.Build.targets',
          'eng/Directory.Build.Common.props','eng/Directory.Build.Common.targets','eng/AzureSDKClient.snk'}
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        prefix,path=member.name.split('/',1)
        assert prefix=='azure-sdk-for-net-8ffa7d7f26bb2c5e3dadf74b2aa9c9ba9c9d9208'
        assert '..' not in Path(path).parts
        if path.startswith('sdk/core/System.ClientModel/') or path in metadata:
            target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
print('PASS full pinned Azure archive and complete ClientModel component/build metadata extraction')
