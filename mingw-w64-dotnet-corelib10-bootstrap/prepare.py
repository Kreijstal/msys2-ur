"""Prepare pinned CoreLib/corerun sources and the original CoreLib generator."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
subprocess.run(['/clang64/bin/python.exe',native(here/'prepare-host.py'),native(root/'runtime-v10.0.5.tar.gz'),native(root)],check=True)
record=json.loads((root/'native-extraction.json').read_text());patch=here/'host-mingw.patch'
r=subprocess.run(['patch','--fuzz=0','--no-backup-if-mismatch','-p1','-i',str(patch)],cwd=root/'r',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
record.update(host_patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),host_patch_log=r.stdout)
(root/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
a=root/'arcade-runtime10-4bf37ce6.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
with tarfile.open(a) as t:
 assert t.pax_headers['comment']=='4bf37ce670528cf2aef4d9b1cd892554b1b02d9d'
 for m in t:
  relative=m.name.partition('/')[2]
  if relative=='src/Microsoft.DotNet.Arcade.Sdk/tools/StrongName.props':
   tree=E.fromstring(t.extractfile(m).read());assert bytes.fromhex(tree.findtext('.//SilverlightPlatformPublicKey'))==bytes.fromhex((here/'inputs/SilverlightPlatform.pubkey.hex').read_text())
  if relative=='src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs':assert t.extractfile(m).read()==(here/'inputs/CalculateAssemblyAndFileVersions.cs').read_bytes()
  if relative=='LICENSE.TXT':(root/'Arcade-LICENSE.TXT').write_bytes(t.extractfile(m).read())
for name in ['prepare-version.py','generate-host-resources.py','prepare-port.py','prepare-generator.py','prepare-corelib.py']:subprocess.run(['/usr/bin/python3',str(here/name),str(root)],check=True)
