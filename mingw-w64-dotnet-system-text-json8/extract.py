"""Extract complete JSON production/generator trees and original shared inputs."""
from pathlib import Path,PurePosixPath
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:])
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bbd5b1651bfc4c75b67ef23b71af58f6441401185f22233daefd35cc9ec72cfd'
out.mkdir()
count=0
with tarfile.open(archive,'r|gz') as tar:
    for member in tar:
        if not member.isfile():continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='runtime-81cabf2857a01351e5ab578947c7403a5b128ad1'
        relative=PurePosixPath(*parts[1:]);assert '..' not in relative.parts
        name=str(relative)
        keep=(name.startswith(('src/libraries/Common/src/','src/libraries/System.Private.CoreLib/src/','eng/')) or
              (name.startswith('src/libraries/System.Text.Json/') and '/tests/' not in name) or
              name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','Directory.Build.props','Directory.Build.targets',
                       'src/libraries/Directory.Build.props','src/libraries/Directory.Build.targets'])
        if keep:
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
            count+=1
print('PASS pinned complete JSON source/generators/shared tree:',count,'files')
