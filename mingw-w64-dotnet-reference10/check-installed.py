"""Validate installed contract bytes, metadata and a fresh NET10 API consumer."""
from pathlib import Path
import shutil,subprocess,sys
root,prepared,out=(Path(p).resolve() for p in sys.argv[1:])
assert not out.exists();out.mkdir()
for name in ['build-status.json','evaluated.json','source-projects.json','NuGet.config']:shutil.copyfile(prepared/name,out/name)
for name in ['keys','stubs']:shutil.copytree(prepared/name,out/name)
refs=Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')
(out/'ref').mkdir();shutil.copytree(refs,out/'ref/net10.0')
for p in (out/'ref/net10.0').glob('*.dll'):assert p.read_bytes()==(prepared/'ref/net10.0'/p.name).read_bytes(),p
subprocess.run(['/usr/bin/python3',str(Path(__file__).resolve().parent/'validate.py'),str(root),str(out),str(refs)],check=True)
print('PASS exact installed contract bytes and fresh complete metadata/NET10 positive/NET8 negative consumer gates')
