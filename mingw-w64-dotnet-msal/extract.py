"""Extract the complete pinned public MSAL repository, preserving every file."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:])
with archive.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='a8d47494284ba9d9743be4c071aea1dc5f1a466a4973f43fbb9e0b23a8d131e9'
out.mkdir()
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        prefix,path=member.name.split('/',1)
        assert prefix=='microsoft-authentication-library-for-dotnet-88df64013795d4e3716e1f677600f8164ffdb542' and '..' not in Path(path).parts
        target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
        with t.extractfile(member) as src,target.open('wb') as dest:shutil.copyfileobj(src,dest)
print('PASS full pinned MSAL repository archive extraction')
