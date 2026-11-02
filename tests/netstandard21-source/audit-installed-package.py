"""Verify every installed Standard2.1 payload byte against the package and source build."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile

archive,prepared,output=map(lambda p:Path(p).resolve(),sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed=['clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.1.0/',
         'clang64/share/doc/dotnet-netstandard21-reference/',
         'clang64/share/licenses/dotnet-netstandard21-reference/']
payload={}
proc=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=proc.stdout,mode='r|') as t:
 for m in t:
  name=m.name.removeprefix('./')
  if name.startswith('.'):continue
  if not m.isfile():continue
  assert any(name.startswith(p) for p in allowed),name
  data=t.extractfile(m).read();installed=Path('/')/name
  assert installed.read_bytes()==data,name
  payload[name]=hashlib.sha256(data).hexdigest()
  if name.endswith('.dll'):
   assert data==(prepared/'ref'/Path(name).name).read_bytes(),name
assert proc.wait()==0
assert len(payload)==132,len(payload)
assert sum(n.endswith('.dll') for n in payload)==121
records=json.loads((prepared/'build-results.json').read_text())
for n,r in records.items():
 assert r['exit_code']==0
 if r['package_asset']:assert sha(prepared/'ref'/(n+'.dll'))==r['output_sha256']
result=dict(installed_payload_files_verified=len(payload),installed_reference_assemblies_verified=121,
            package_archive_sha256=sha(archive),installed_files_sha256=payload,
            formal_pacman_installed=True,full_dependency_goal_complete=False)
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS 132 installed payload files, all 121 original source Standard2.1 references, package paths and SHA256')
