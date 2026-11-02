"""Check installed archive bytes and execute an isolated original-profile consumer."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;doc=prefix/'share/doc/dotnet-newtonsoft-json1303-bootstrap'
for rel,h in json.loads((doc/'payload-sha256.json').read_text()).items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
build=out/'build';build.mkdir();(build/'results.json').write_bytes((doc/'build-results.json').read_bytes())
with zipfile.ZipFile(prefix/'lib/dotnet/library-packs/newtonsoft.json.13.0.3.nupkg') as z:(build/'Newtonsoft.Json.dll').write_bytes(z.read('lib/netstandard2.0/Newtonsoft.Json.dll'))
subprocess.run([sys.executable,'-X','utf8',here/'check.py',build,out/'consumer',here/'JsonConvertTest.cs'],check=True)
print('PASS installed package inventory, original NETStandard2 archive and isolated source consumer')
