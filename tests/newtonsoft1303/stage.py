"""Stage the exact 13.0.3 original NETStandard2 source package."""
from pathlib import Path
import hashlib,json,shutil,sys,tarfile,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;build=root/'build';result=json.loads((build/'results.json').read_text())
assert result['exit_code']==0 and result['original_production_source_changes']==0
feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True)
nuspec='<?xml version="1.0"?><package><metadata><id>Newtonsoft.Json</id><version>13.0.3</version><authors>James Newton-King</authors><description>Original Newtonsoft.Json13.0.3 NETStandard2 source bootstrap profile</description><license type="expression">MIT</license><repository type="git" url="https://github.com/JamesNK/Newtonsoft.Json"/><dependencies><group targetFramework="netstandard2.0"/></dependencies></metadata></package>'
with zipfile.ZipFile(feed/'newtonsoft.json.13.0.3.nupkg','w',zipfile.ZIP_DEFLATED) as z:
    for n,data in [('Newtonsoft.Json.nuspec',nuspec.encode()),('LICENSE.md',(build/'source/LICENSE.md').read_bytes())]+[('lib/netstandard2.0/Newtonsoft.Json.'+ext,(build/('Newtonsoft.Json.'+ext)).read_bytes()) for ext in ['dll','pdb','xml']]:
        info=zipfile.ZipInfo(n,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
doc=prefix/'share/doc/dotnet-newtonsoft-json1303-bootstrap';doc.mkdir(parents=True)
for src,dest in [(build/'results.json','build-results.json'),(root/'check/results.json','build-check-results.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/dest)
checks=doc/'checks';checks.mkdir()
for n in ['check.py','Check.cs','check-installed.py']:shutil.copyfile(here/n,checks/n)
with tarfile.open(root/'newtonsoft-json-13.0.3.tar.gz') as t:
    m=next(m for m in t if m.name.endswith('/Src/Newtonsoft.Json.Tests/JsonConvertTest.cs'));(checks/'JsonConvertTest.cs').write_bytes(t.extractfile(m).read())
license=prefix/'share/licenses/dotnet-newtonsoft-json1303-bootstrap';license.mkdir(parents=True);shutil.copyfile(build/'source/LICENSE.md',license/'LICENSE.md')
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS staged original NETStandard2 package with source manifest and upstream regression fixtures')
