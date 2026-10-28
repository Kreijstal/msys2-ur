"""Extract complete pinned Abstractions production/build/test inputs."""
from pathlib import Path
import hashlib,shutil,sys,tarfile

archive,out=(Path(p) for p in sys.argv[1:]);out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='c8bb5a2b1a946b98dc7165ed8e01439b76cc2d91c1b3ab168e613f0120b763f2'
with tarfile.open(archive,'r|gz') as t:
    for member in t:
        if not member.isfile():continue
        root,relative=member.name.split('/',1)
        assert root=='azure-activedirectory-identitymodel-extensions-for-dotnet-c94c7fc235501d478221e979062bd8837a55575b'
        assert '..' not in Path(relative).parts
        if relative.startswith(('src/Microsoft.IdentityModel.Abstractions/','test/Microsoft.IdentityModel.Abstractions.Tests/','build/')) or relative in ['LICENSE.txt','buildConfiguration.xml','updateAssemblyInfo.ps1']:
            target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as src,target.open('wb') as dest:shutil.copyfileobj(src,dest)
print('PASS pinned complete original Abstractions production/build/test inputs')
