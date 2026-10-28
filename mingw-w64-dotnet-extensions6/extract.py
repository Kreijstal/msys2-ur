"""Extract complete selected library sources/shared inputs from the pinned archive."""
from pathlib import Path
import shutil
import sys
import tarfile

archive,out=(Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
prefix='runtime-4822e3c3aa77eb82b2fb33c9321f923cf11ddde6/'
folders=tuple('src/libraries/'+name+'/src/' for name in [
    'Microsoft.Extensions.Primitives','Microsoft.Extensions.FileProviders.Abstractions','Microsoft.Extensions.FileSystemGlobbing'])
files={'LICENSE.TXT','src/libraries/Directory.Build.props',
       'src/libraries/Common/src/System/SR.cs','src/libraries/Common/src/Extensions/EmptyDisposable.cs',
       'src/libraries/System.Private.CoreLib/src/System/Numerics/Hashing/HashHelpers.cs'}
count=0
with tarfile.open(archive,mode='r|gz') as t:
    for member in t:
        if member.name==prefix.rstrip('/'):continue
        assert member.name.startswith(prefix),member.name
        name=member.name[len(prefix):]
        if not member.isfile() or not (name.startswith(folders) or name in files):continue
        relative=Path(name);assert not relative.is_absolute() and '..' not in relative.parts
        target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with t.extractfile(member) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
        count+=1
print('Extracted complete three-library source trees/shared inputs into short source root:',count,'files')
