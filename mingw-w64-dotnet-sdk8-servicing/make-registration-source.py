"""Freeze the small source SDK registration repair workflow."""
from pathlib import Path
import gzip,tarfile,hashlib,re
root=Path(__file__).resolve().parent
source=root.parent/'tests/sdk8-servicing'
files=[source/'register-netstandard21.py',*[source/'inputs'/('installer8-'+n) for n in ['GenerateBundledVersions.targets','Versions.props','framework-metadata-source.json','LICENSE.TXT']]]
p=root/'dotnet-sdk8-registration-source-1.tar.gz'
with p.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
 for f in files:
  info=t.gettarinfo(str(f),'sdk-registration/'+f.relative_to(source).as_posix());info.mtime=info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o644
  with f.open('rb') as stream:t.addfile(info,stream)
sha=hashlib.sha256(p.read_bytes()).hexdigest()
r=root/'PKGBUILD';s=r.read_text();group=re.search(r'sha256sums=\((.*?)\)',s,re.S);matches=list(re.finditer(r"'[^']*'",group[1]));old=matches[1];a=group.start(1)+old.start();b=group.start(1)+old.end();s=s[:a]+"'"+sha+"'"+s[b:];r.write_text(s)
print(sha,len(files),'workflow files')
