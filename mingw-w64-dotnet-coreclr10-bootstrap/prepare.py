"""Prepare the exact native host/CoreCLR port and original source cDAC tool."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
subprocess.run(['/clang64/bin/python.exe',native(here/'prepare-host.py'),native(root/'runtime-v10.0.5.tar.gz'),native(root)],check=True)
record=json.loads((root/'native-extraction.json').read_text());patch=here/'host-mingw.patch'
result=subprocess.run(['patch','--fuzz=0','--no-backup-if-mismatch','-p1','-i',str(patch)],cwd=root/'r',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
record.update(host_patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),host_patch_log=result.stdout,full_runtime10_built=False,full_sdk10_built=False)
(root/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
# Original Arcade version task and keys are bound to the runtime VMR pin.
a=root/'arcade-runtime10-4bf37ce6.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
with tarfile.open(a) as t:
 assert t.pax_headers['comment']=='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d'
 for m in t:
  if m.name.endswith('/src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs'):
   assert t.extractfile(m).read()==(here/'inputs/CalculateAssemblyAndFileVersions.cs').read_bytes()
  if m.name.partition('/')[2]=='LICENSE.TXT':(root/'Arcade-LICENSE.TXT').write_bytes(t.extractfile(m).read())
for script in ['prepare-version.py','generate-host-resources.py','prepare-port.py']:subprocess.run(['/usr/bin/python3',str(here/script),str(root)],check=True)
subprocess.run(['/usr/bin/python3',str(here/'prepare-cdac.py'),str(root),str(root/'command-line-api-source.tar.gz')],check=True)
